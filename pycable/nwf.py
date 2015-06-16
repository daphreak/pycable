# nwf.py
#
# Copyright 2015 Stuart Donnan
#
# This file is part of Pycable.
#
# Pycable is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 2 of the License, or (at your option) any later
# version.
#
# Pycable is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Pycable. If not, see http://www.gnu.org/licenses/.
'''
Provides parsing and writing of NWF files
'''

from pyparsing import *

def parseNWF(nwfStr):
    '''
    Parse and NWF file from a string

    Currently does not handle cables (multi-conductor spools). Pro Tip: If you
    are trying to understand this code it helps to work bottom up from the nwf
    definition.

    Args:
        nwfStr: A string containing NWF format information

    Returns:
        ( {Spools}, {Connectors}, {Connections} )
    '''

    wspools = {}
    connectors = {}
    connections = {}

    def checkRedef(k,d,t,loc):
        '''
        Args:
            k: key to check
            d: dict to check in
            t: string type name for error message (what got redefined)
            loc: current location
        '''
        if k in d:
            raise Exception('Line {}: Redefinition of {} {}'.format(
                lineno(loc,nwfStr),t,k))

    def params2dict(s,loc,toks):
        d = {}
        for p in toks[0]:
            checkRedef(p.key,d,'Parameter',p.loc)
            d[p.key] = p.value
        toks['param_dict'] = d
        return toks

    def pins2dict(s,loc,toks):
        d = {}
        for p in toks[0]:
            checkRedef(p.id,d,'Pin',p.loc)
            d[p.id] = p.param_dict
        toks['pin_dict'] = d
        return toks

    def storeLoc(s,loc,toks):
        toks['loc'] = loc
        return toks

    def defSpool(s,loc,toks):
        checkRedef(toks.id, wspools, 'Wire Spool', loc)
        wspools[toks.id] = toks.parameters.param_dict

    def defConnector(s,loc,toks):
        checkRedef(toks.id, connectors, 'Connector', loc)
        connectors[toks.id] = (toks.parameters.param_dict,toks.pins.pin_dict)

    def checkWireEndpoint(conn, pin, loc):
        if conn not in connectors:
            raise Exception('Line {}: Bad wire definition, undefined connector {}'.format(
                lineno(loc,nwfStr),conn))
        if pin not in connectors[conn][1]:
            raise Exception('Line {}: Bad wire definition, undefined pin {} for connector {}'.format(
                lineno(loc,nwfStr),pin,conn))

    def defConnection(s,loc,toks):
        checkRedef(toks.id, connections, 'Wire', loc)
        src = (toks.fromConn,toks.fromPin)
        dst = (toks.toConn,toks.toPin)
        checkWireEndpoint(*src,loc=loc)
        checkWireEndpoint(*dst,loc=loc)
        connections[toks.id] = (src,dst)

    # grammar configuration with parsing actions
    kwnew = Suppress(Keyword("new",caseless=True))
    ident = Word( alphas + nums + "_-")
    decimal = Combine(Optional(Word("+-",max=1)) + Word(nums) + Optional('.' + Word(nums)))
    value = dblQuotedString.setParseAction(removeQuotes) ^ decimal ^ ident
    comment = Literal("!") + SkipTo(lineEnd)
    parameter = Group(Suppress(Keyword("parameter",caseless=True)) + ident.setResultsName('key').setParseAction(storeLoc) + value.setResultsName('value'))
    param_list = Group(ZeroOrMore( parameter )).setParseAction(params2dict)
    wspool = kwnew + Keyword("wire_spool",caseless=True) + ident.setResultsName('id') + \
             param_list.setResultsName('parameters')
    wire = kwnew + Keyword("wire",caseless=True) + ident.setResultsName('id') + \
           ident.setResultsName('type') + \
           Keyword("attach",caseless=True) + \
           ident.setResultsName('fromConn') + ident.setResultsName('fromPin') + \
           ident.setResultsName('toConn')   + ident.setResultsName('toPin')
    pin = Group(Keyword("pin",caseless=True) + ident.setResultsName('id').setParseAction(storeLoc) + param_list)
    pin_list = Group(ZeroOrMore(pin)).setResultsName('pins').setParseAction(pins2dict)
    connector = kwnew + Keyword("connector",caseless=True) + ident.setResultsName('id') + \
             param_list.setResultsName('parameters') + pin_list.setResultsName('pins')

    nwf = OneOrMore(wspool.setParseAction(defSpool) | \
                    connector.setParseAction(defConnector) | \
                    wire.setParseAction(defConnection))
    nwf.ignore(comment)
    nwf.parseString(nwfStr)
    return (wspools,connectors,connections)
