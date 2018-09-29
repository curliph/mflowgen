from pymtl      import * 
from pclib.ifcs import InValRdyBundle, OutValRdyBundle
from pclib.rtl  import Mux, RegEn, Reg
from pclib.ifcs import MemReqMsg, MemRespMsg
from pclib.rtl  import SingleElementBypassQueue, SingleElementPipelinedQueue

#  config structure
#             clog2(nports)                      
#                 nbits      51:42      41:32        31:0
#  +----------+------------+-------+------------+---------------+
#  | reserved |  out_sel   | count |   stride   |   base_addr   |
#  +----------+------------+-------+------------+---------------+#


class LdPePRTL ( Model ):
  
  def __init__( s, nports = 4, DataBits = 32, ConfigBits = 64,
                MemBits = 128 ):

    # local params
    sel_bits     = clog2( nports )
    opaque_bits  = 8
    addr_bits    = 32
    cnt_bits     = 10
    stride_bits  = 10
    stride_mult  = MemBits / 8
    stride_end   = addr_bits + stride_bits
    cnt_end      = stride_end + cnt_bits
    sel_end      = cnt_end + sel_bits
    ser_maxcnt   = MemBits / 32

    # config input 
    s.config = InPort( ConfigBits )

    # state signals
    s.go   = InPort ( 1 )
    s.idle = OutPort( 1 )

    # IO interface
    s.out    = OutValRdyBundle  [ nports ]( DataBits )
    
    # memory interface
    s.memreq  = OutValRdyBundle ( MemReqMsg( opaque_bits, addr_bits, MemBits ) )
    s.memresp = InValRdyBundle  ( MemRespMsg( opaque_bits, MemBits ) )

    # mem queues
    s.memreq_q  = SingleElementBypassQueue( MemReqMsg( opaque_bits, addr_bits, MemBits ) )
    s.connect( s.memreq, s.memreq_q.deq )

    s.memresp_q = SingleElementPipelinedQueue( MemRespMsg( opaque_bits, MemBits ) )
    s.connect( s.memresp, s.memresp_q.enq )

    # config reg
    s.config_reg = m = RegEn( ConfigBits )
    s.connect( m.in_,  s.config )
    
    # addr reg
    s.addr_reg = Reg( DataBits )
    
    # cnt reg
    s.cnt_reg  = Reg( cnt_bits )

    # deq reg
    s.deq_reg = m = RegEn( MemBits )
    s.connect( m.in_, s.memresp_q.deq.msg.data )

    # serialize cnt reg
    s.sercnt_reg = Reg( DataBits )

    @s.combinational
    def comb_config_en():
      s.config_reg.en.value = s.go & s.idle

    # config field signals
    s.out_sel   = Wire( sel_bits    )
    s.cnt       = Wire( cnt_bits    )
    s.stride    = Wire( stride_bits )
    s.base_addr = Wire( addr_bits   )

    s.connect_pairs(
      s.base_addr,  s.config_reg.out[ 0          : addr_bits  ],
      s.stride,     s.config_reg.out[ addr_bits  : stride_end ],
      s.cnt,        s.config_reg.out[ stride_end : cnt_end    ],
      s.out_sel,    s.config_reg.out[ cnt_end    : sel_end    ],
    )
    
    # interal state 
    s.state = Wire( 2 )

    s.STATE_IDLE  = Bits( 2, 0 )
    s.STATE_SEND0 = Bits( 2, 1 )
    s.STATE_SEND1 = Bits( 2, 2 )
    s.STATE_WAIT  = Bits( 2, 3 )

    s.mem_done = Wire( cnt_bits )
    
    # state transition

    @s.tick_rtl
    def stat_update():
      if s.reset:
        s.state.next = s.STATE_IDLE
      else:
        s.state.next = s.state

        if s.state == s.STATE_IDLE:
          if s.go:
            s.state.next   = s.STATE_SEND0
        
        elif s.state == s.STATE_SEND0:
          if s.memreq_q.enq.rdy:
            if s.cnt <= 1:
              s.state.next = s.STATE_WAIT
            else:
              s.state.next = s.STATE_SEND1

        elif s.state == s.STATE_SEND1:
          if ( s.cnt_reg.out == 1 ) and s.memreq_q.enq.rdy:
            s.state.next = s.STATE_WAIT

        elif s.state == s.STATE_WAIT:
          if s.mem_done == s.cnt:
            s.state.next = s.STATE_IDLE

    # state output

    @s.combinational
    def comb_state_output():

      s.memreq_q.enq.val.value  = 0
      s.cnt_reg.in_.value       = s.cnt_reg.out
      s.addr_reg.in_.value      = s.addr_reg.out

      if s.state == s.STATE_IDLE:
        s.idle.value          = 1
        s.mem_done.value      = 0
        s.sercnt_reg.in_.value = 0

      elif s.state == s.STATE_SEND0:
        s.idle.value = 0
        
        if s.memreq_q.enq.rdy:
          s.memreq_q.enq.msg.type_.value = MemReqMsg.TYPE_READ
          s.memreq_q.enq.msg.addr.value  = s.base_addr
          s.memreq_q.enq.msg.len.value   = 0
          s.memreq_q.enq.val.value = 1

        if s.cnt > 1:
          s.cnt_reg.in_.value  = s.cnt - 1
          s.addr_reg.in_.value = s.base_addr + s.stride * stride_mult

      elif s.state == s.STATE_SEND1:
        s.idle.value = 0

        if s.memreq_q.enq.rdy:
          s.memreq_q.enq.msg.type_.value = MemReqMsg.TYPE_READ
          s.memreq_q.enq.msg.addr.value  = s.addr_reg.out
          s.memreq_q.enq.msg.len.value   = 0
          s.memreq_q.enq.val.value = 1

          s.cnt_reg.in_.value  = s.cnt_reg.out - 1
          s.addr_reg.in_.value = s.addr_reg.out + s.stride * stride_mult
      
      elif s.state == s.STATE_WAIT:
        s.idle.value = 0


    @s.combinational
    def comb_memresp_deq():
      s.sercnt_reg.in_.value = s.sercnt_reg.out
      s.mem_done.value       = s.mem_done

      s.deq_reg.en.value        = (s.sercnt_reg.out == 0) & s.memresp_q.deq.val
      s.memresp_q.deq.rdy.value = (s.sercnt_reg.out == 0)
      
      if s.deq_reg.en:
        s.sercnt_reg.in_.value = ser_maxcnt

      for i in xrange( nports ):
        if  i == s.out_sel :
          s.out[i].val.value = 0
          if  s.sercnt_reg.out > 0:
            s.out[i].msg.value = s.deq_reg.out[ DataBits*( ser_maxcnt - s.sercnt_reg.out ):
                                                DataBits*( ser_maxcnt - s.sercnt_reg.out + 1 ) ]
            s.out[i].val.value = 1
          if s.out[i].val and s.out[i].rdy:
            s.sercnt_reg.in_.value = s.sercnt_reg.out - 1
            s.mem_done.value       = s.mem_done + 1
        
        else:
          s.out[i].val.value = 0
      

  def line_trace(s):
    return "({}|{}|{}) ({}:{}:{}) ({}:{}:{}) | ({}:{}:{}) >> {}:{}({}|{})".format(
      s.go, s.idle, s.state, s.cnt, s.stride, s.base_addr,
      s.memreq.val, s.memreq.rdy, s.memreq.msg,
      s.memresp.val, s.memresp.rdy, s.memresp.msg,
      s.out_sel, s.out[s.out_sel].msg, s.out[s.out_sel].val,s.out[s.out_sel].rdy)