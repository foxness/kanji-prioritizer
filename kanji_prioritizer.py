import os

import urllib.parse
import re
import operator
import types
import shlex

from aqt import mw, gui_hooks
from anki.utils import ids2str
from aqt.utils import show_info

# from aqt.qt import *
# from aqt import Collection

from . import util, data, config_util

def get_units(mw, config):
    deck_ids = [config.did]
    if config.did == "*":
        deck_ids = mw.col.decks.all_ids()
    
    for deck_id in deck_ids:
        for _, id_ in mw.col.decks.children(int(deck_id)):
            deck_ids.append(id_)
    
    card_ids = []
    
    if len(config.searchfilter) > 0 and len(config.fieldslist) > 0 and len(deck_ids) > 0:
        card_ids = mw.col.find_cards("(" + util.make_query(deck_ids, config.fieldslist) + ") " + config.searchfilter)
    else:
        card_ids = mw.col.db.list("select id from cards where did in %s or odid in %s" % (ids2str(deck_ids), ids2str(deck_ids)))

    units = dict()
    notes = dict()
    for i in card_ids:
        card = mw.col.get_card(i)
        
        if card.nid not in notes.keys():
            keys = card.note().keys()
            unitKey = set()
            matches = operator.eq
            
            for keyword in config.fieldslist:
                for key in keys:
                    if matches(key.lower(), keyword):
                        unitKey.update(set(card.note()[key]))
                        break
            
            notes[card.nid] = unitKey
        else:
            unitKey = notes[card.nid]
        
        if unitKey is not None:
            for ch in unitKey:
                util.addUnitData(units, ch, i, card, config.kanjionly)
    
    return units

def run_prioritizer():
    data.init_groups()
    
    config = types.SimpleNamespace(**config_util.get_config(mw))
    
    config.did = '*'
    config.fieldslist = ['expression']
    config.sortby = util.SortOrder.FREQUENCY
    
    units = get_units(mw, config)
    
    unitsList = {
        util.SortOrder.NONE:      sorted(units.values(), key=lambda unit: (unit.idx, unit.known_count)),
        util.SortOrder.UNICODE:   sorted(units.values(), key=lambda unit: (util.safe_unicodedata_name(unit.value), unit.known_count)),
        util.SortOrder.SCORE:     sorted(units.values(), key=lambda unit: (util.scoreAdjust(unit.avg_interval / config.interval), unit.known_count), reverse=True),
        util.SortOrder.FREQUENCY: sorted(units.values(), key=lambda unit: (unit.known_count, util.scoreAdjust(unit.avg_interval / config.interval)), reverse=True),
    }[util.SortOrder(config.sortby)]
        
    total_count = 0
    count_known = 0
    unknown_units = []
    for unit in unitsList:
        total_count += 1
        
        is_known = unit.known_count > 0
        if is_known:
            count_known += 1
        else:
            unknown_units.append(unit)
    
    unknown_units = sorted(unknown_units, key=lambda unit: unit.unknown_count, reverse=True)
    # show_info(f'unknown_units[:3]: {unknown_units[:3]}')