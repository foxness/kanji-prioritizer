import os

import urllib.parse
import re
import operator

from functools import reduce
from datetime import datetime
from anki.utils import ids2str
from aqt.utils import show_info

# from aqt.qt import *
# from aqt import Collection

from . import util, data, config_util

import types
import shlex

from aqt import mw, gui_hooks
# from aqt.webview import AnkiWebView
# from aqt.qt import (QAction, QSizePolicy, QDialog, QHBoxLayout,
#                     QVBoxLayout, QTabWidget, QLabel, QCheckBox, QSpinBox,
#                     QComboBox, QPushButton, QLineEdit, Qt, qconnect,
#                     QScrollArea, QWidget, QMessageBox, QDateTimeEdit,
#                     QDateTime)

def kanjigrid(mw, config):
    dids = [config.did]
    if config.did == "*":
        dids = mw.col.decks.all_ids()
    for deck_id in dids:
        for _, id_ in mw.col.decks.children(int(deck_id)):
            dids.append(id_)
    cids = []
    #mw.col.find_cards and mw.col.db.list sort differently
    #mw.col.db.list is kept due to some users being very picky about the order of kanji when using `Sort by: None`
    if len(config.searchfilter) > 0 and len(config.fieldslist) > 0 and len(dids) > 0:
        cids = mw.col.find_cards("(" + util.make_query(dids, config.fieldslist) + ") " + config.searchfilter)
    else:
        cids = mw.col.db.list("select id from cards where did in %s or odid in %s" % (ids2str(dids), ids2str(dids)))

    units = dict()
    notes = dict()
    for i in cids:
        card = mw.col.get_card(i)
        
        # tradeoff between branching and mutating here vs collecting all the cards and then filtermapping
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
    # config.searchfilter = ''
    # config.interval = 180
    # config.groupby = groupby.currentIndex()
    config.sortby = util.SortOrder.NONE
    # config.lang = pagelang.currentText()
    # config.unseen = True
    
    units = kanjigrid(mw, config)
    
    unitsList = {
        util.SortOrder.NONE:      sorted(units.values(), key=lambda unit: (unit.idx, unit.count)),
        util.SortOrder.UNICODE:   sorted(units.values(), key=lambda unit: (util.safe_unicodedata_name(unit.value), unit.count)),
        util.SortOrder.SCORE:     sorted(units.values(), key=lambda unit: (util.scoreAdjust(unit.avg_interval / config.interval), unit.count), reverse=True),
        util.SortOrder.FREQUENCY: sorted(units.values(), key=lambda unit: (unit.count, util.scoreAdjust(unit.avg_interval / config.interval)), reverse=True),
    }[util.SortOrder(config.sortby)]
        
    total_count = 0
    count_known = 0
    for unit in unitsList:
        if unit.count != 0 or config.unseen:
            total_count += 1
            bgcolor = util.get_background_color(unit.avg_interval, config.interval, unit.count)
            if unit.count != 0 or bgcolor not in ["#E62E2E", "#FFF"]:
                count_known += 1
            # table += kanjitile(unit.value, bgcolor, total_count, unit.avg_interval)
            
    
    # unknown_units = []
    
    show_info(f'Total Count: {total_count}, Known: {count_known}')