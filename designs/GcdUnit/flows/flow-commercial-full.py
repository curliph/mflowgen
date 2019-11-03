#! /usr/bin/env python
#=========================================================================
# setup_graph.py
#=========================================================================
# Demo with 16-bit GcdUnit
#
# Author : Christopher Torng
# Date   : June 2, 2019
#

import os
import sys

if __name__ == '__main__':
  sys.path.append( '../..' )

from mflow.components import Graph, Step

#-------------------------------------------------------------------------
# setup_graph
#-------------------------------------------------------------------------

def setup_graph():

  g = Graph()

  #-----------------------------------------------------------------------
  # Parameters
  #-----------------------------------------------------------------------

  adk_name = 'freepdk-45nm'
  adk_view = 'view-standard'

  parameters = {
    'design_name'  : 'GcdUnit',
    'clock_period' : 2.0,
    'adk'          : adk_name,
    'adk_view'     : adk_view,
  }

  #-----------------------------------------------------------------------
  # ADK
  #-----------------------------------------------------------------------

  g.set_adk( adk_name )

  #-----------------------------------------------------------------------
  # Import steps
  #-----------------------------------------------------------------------

  this_dir = os.path.dirname( os.path.abspath( __file__ ) )

  # ADK step

  adk = g.get_adk_step()

  # Custom steps

  rtl = Step( this_dir + '/rtl' )

  # Default steps

  info         = Step( 'info',                         default=True )
  constraints  = Step( 'constraints',                  default=True )
  dc           = Step( 'synopsys-dc-synthesis',        default=True )
  iflow        = Step( 'cadence-innovus-flowgen',      default=True )
  iplugins     = Step( 'cadence-innovus-plugins',      default=True )
  init         = Step( 'cadence-innovus-init',         default=True )
  place        = Step( 'cadence-innovus-place',        default=True )
  cts          = Step( 'cadence-innovus-cts',          default=True )
  postcts_hold = Step( 'cadence-innovus-postcts_hold', default=True )
  route        = Step( 'cadence-innovus-route',        default=True )
  postroute    = Step( 'cadence-innovus-postroute',    default=True )
  signoff      = Step( 'cadence-innovus-signoff',      default=True )

  #-----------------------------------------------------------------------
  # Parameterize
  #-----------------------------------------------------------------------

  adk.update_params( parameters )
  info.update_params( parameters )
  dc.update_params( parameters )
  constraints.update_params( parameters )
  iflow.update_params( parameters )

  #-----------------------------------------------------------------------
  # Graph -- Add nodes
  #-----------------------------------------------------------------------

  g.add_step( info         )
  g.add_step( rtl          )
  g.add_step( constraints  )
  g.add_step( dc           )
  g.add_step( iflow        )
  g.add_step( iplugins     )
  g.add_step( init         )
  g.add_step( place        )
  g.add_step( cts          )
  g.add_step( postcts_hold )
  g.add_step( route        )
  g.add_step( postroute    )
  g.add_step( signoff      )

  #-----------------------------------------------------------------------
  # Graph -- Add edges
  #-----------------------------------------------------------------------

  # Connect by name

  g.connect_by_name( adk,      dc           )
  g.connect_by_name( adk,      iflow        )
  g.connect_by_name( adk,      init         )
  g.connect_by_name( adk,      place        )
  g.connect_by_name( adk,      cts          )
  g.connect_by_name( adk,      postcts_hold )
  g.connect_by_name( adk,      route        )
  g.connect_by_name( adk,      postroute    )
  g.connect_by_name( adk,      signoff      )

  g.connect_by_name( rtl,         dc        )
  g.connect_by_name( constraints, dc        )

  g.connect_by_name( dc,       iflow        )
  g.connect_by_name( dc,       init         )
  g.connect_by_name( dc,       place        )
  g.connect_by_name( dc,       cts          )

  g.connect_by_name( iplugins, iflow        )
  g.connect_by_name( iplugins, init         )
  g.connect_by_name( iplugins, place        )
  g.connect_by_name( iplugins, cts          )
  g.connect_by_name( iplugins, postcts_hold )
  g.connect_by_name( iplugins, route        )
  g.connect_by_name( iplugins, postroute    )
  g.connect_by_name( iplugins, signoff      )

  g.connect_by_name( iflow,    init         )
  g.connect_by_name( iflow,    place        )
  g.connect_by_name( iflow,    cts          )
  g.connect_by_name( iflow,    postcts_hold )
  g.connect_by_name( iflow,    route        )
  g.connect_by_name( iflow,    postroute    )
  g.connect_by_name( iflow,    signoff      )

  g.connect_by_name( init,         place        )
  g.connect_by_name( place,        cts          )
  g.connect_by_name( cts,          postcts_hold )
  g.connect_by_name( postcts_hold, route        )
  g.connect_by_name( route,        postroute    )
  g.connect_by_name( postroute,    signoff      )

  return g


if __name__ == '__main__':
  g = setup_graph()
#  g.plot()
