#!/usr/bin/env python3

"""
    File name: update.translation.py
    Author: Niklas Wagner <skaronator.com>
	Contributors:
		* None
    Date created: 2017-03-07
    Date last modified: 2017-03-07
    Python Version: 3.4
	Dependencies:
		* https://pypi.python.org/pypi/polib
	
	
	This script create and update the language file (.po files) with the newest translation from Transiflex.
	
	https://www.transifex.com/plex-1/plex-web/en-usjson/
	
	
	Todo:
		* Download newest translation from Plex Web Repo instead of using local files.
		* Host the "PlexForKodi" translation strings on Transiflex or integrate it in the Plex Web Transiflex Repo.
		* Maybe add PMS Transiflex as well since some strings are missing in Plex Web but in PMS (Quality Settings for example)
		
	Translation Todo:
		* Merge "By Date Added", "By Release Date" with "By {1}" translation
		* Replace "Searching..." with "Searching for {1}"?
		* Merge "Couldn't reach plex.tv" and "Make sure your device is connected to the internet"

		
	Translation compromise:
		* "Force" -> "Forced"
		* "This item is currently unavailable." -> "File unavailable"
		* "Switch User" -> "Switch User..."
		* "Shows" -> "TV Shows"
		* "Camera Make" -> "Make"
		* "Camera Model" -> "Model"
		* "Shutter Speed" -> "Exposure"
		* "Shutdown" -> "Power Off"
		* "Hibernate" -> "Suspend"
		* "Choose Version" -> "Select a version"
		* "No Content available for this filter" -> "Can't find anything matching your current filters."
		* "Server is not accessible. Please sign into your server and check your connection." -> "This server is offline or unreachable"
"""


import os
import json
import codecs
import polib
from pprint import pprint


def main():
	script_dir = os.path.dirname(os.path.realpath(__file__))
	
	PlexWeb_dir = os.path.join(script_dir, "Transiflex")
	pfkTranslation_dir = os.path.join(script_dir, "PlexForKodi")
	
	StringMatches = os.path.join(script_dir, "translation.matches.json")
	
	#language_dir = os.path.join(script_dir, "Temp")
	language_dir = os.path.abspath(script_dir+"/../../resources/language")
	
	
	print("script_dir: "+script_dir)
	print("language_dir: "+language_dir)
	
	
	defaultLanguage = ['English', 'en_US', 'en_gb']
	
	supportedLanguages = [
		defaultLanguage,
		#<Kodi Folder Name>, <Search String in Filename>, <language tag in .po files>
		['German', 'de', 'de_DE'],
		['Danish', 'da', 'da_DK'],
		['Spanish', 'es_ES', 'es'],
		['French', 'fr', 'fr'],
		['Russian', 'ru', 'ru']
	]
	
	StringMatches_data = json.load(codecs.open(StringMatches, 'r', 'utf-8-sig'))
	
	transiflex_file_default = os.path.join(PlexWeb_dir, "for_use_plex-web_en-usjson_"+defaultLanguage[1]+".json")
	transiflex_data_default = json.load(codecs.open(transiflex_file_default, 'r', 'utf-8-sig'))
	
	pfk_file_default = os.path.join(pfkTranslation_dir, "plex_for_kodi_"+defaultLanguage[1]+".json")
	pfk_data_default = json.load(codecs.open(pfk_file_default, 'r', 'utf-8-sig'))

	
	for language in supportedLanguages:
	
		transiflex_data = {}
		if language[0] != defaultLanguage[0]:
			transiflex_file = os.path.join(PlexWeb_dir, "for_use_plex-web_en-usjson_"+language[1]+".json")
			if os.path.isfile(transiflex_file):
				transiflex_data = json.load(codecs.open(transiflex_file, 'r', 'utf-8-sig'))
				
		pfk_data = {}
		if language[0] != defaultLanguage[0]:
			pfk_file = os.path.join(pfkTranslation_dir, "plex_for_kodi_"+language[1]+".json")
			if os.path.isfile(pfk_file):
				pfk_data = json.load(codecs.open(pfk_file, 'r', 'utf-8-sig'))

		
		po = setupFile(language[0], language[2])
		po = matchTransiflex(po, StringMatches_data, transiflex_data, transiflex_data_default)
		po = matchPFK(po, pfk_data, pfk_data_default)
		
		save_dir = language_dir+"/"+language[0]
		
		if not os.path.exists(save_dir):
			os.makedirs(save_dir)
		
		po.save(save_dir+"/strings.po")
		#pprint(transiflex_data)
	
def setupFile(language, languageShort):
	po = polib.POFile()
		
	po.metadata = {
		'Project-Id-Version': 'XBMC-Addons',
		'Report-Msgid-Bugs-To': 'alanwww1@xbmc.org',
		'POT-Creation-Date': 'YYYY-MM-DD 00:00+0100',
		'PO-Revision-Date': 'YYYY-MM-DD 00:00+0100',
		'Last-Translator': 'FULL NAME <EMAIL@ADDRESS>',
		'Language-Team': language[0],
		'MIME-Version': '1.0',
		'Content-Type': 'text/plain; charset=UTF-8',
		'Content-Transfer-Encoding': '8bit',
		'Language': language[2],
		'Plural-Forms': 'nplurals=2; plural=(n != 1);'
	}
	return po
	
def matchTransiflex(po, StringMatches_data, transiflex_data, defaultData):
	for matchSTR, matchIDs in StringMatches_data.items():
		# Convert String to Array
		if not isinstance(matchIDs, list):
			matchIDs = [matchIDs]

		if matchSTR in transiflex_data:
			for matchID in matchIDs:
				entry = polib.POEntry(
					msgctxt = matchID,
					msgid=defaultData[matchSTR],
					msgstr=transiflex_data[matchSTR]
				)
			
				po.append(entry)
		else:
			for matchID in matchIDs:
				entry = polib.POEntry(
					msgctxt = matchID,
					msgid=defaultData[matchSTR],
					msgstr=""
				)
			
				po.append(entry)
				
	return po

def matchPFK(po, pfk_data, defaultData):
	if len(pfk_data) > 0:
		for matchID, matchSTR in pfk_data.items():
			defaultData.pop(matchID, None)
			entry = polib.POEntry(
					msgctxt=matchID,
					msgid=defaultData[matchID],
					msgstr=matchSTR
				)
			po.append(entry)
	if len(defaultData) > 0:	
		for matchID, matchSTR in defaultData.items():
			entry = polib.POEntry(
					msgctxt=matchID,
					msgid=matchSTR,
					msgstr=""
				)
			po.append(entry)
	return po


main()