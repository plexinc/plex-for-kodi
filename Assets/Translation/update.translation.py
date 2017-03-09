#!/usr/bin/env python3

"""
    File name: update.translation.py
    Author: Niklas Wagner (skaronator.com)
	Contributors:
		* None
    Date created: 2017-03-07
    Date last modified: 2017-03-09
    Python Version: 3.5
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

"""


import os
import json
import codecs
import polib
import collections

def main():
	script_dir = os.path.dirname(os.path.realpath(__file__))
	PlexWeb_dir = os.path.join(script_dir, "Transiflex")
	pfkTranslation_dir = os.path.join(script_dir, "PlexForKodi")
	language_dir = os.path.abspath(script_dir+"/../../resources/language")
	
	
	defaultLanguage = ['English', 'en_US', 'en_gb']
	
	supportedLanguages = [
		defaultLanguage,
		#<Kodi Folder Name>, <Search String in Filename>, <language tag in .po files>
		['German', 'de', 'de_DE'],
		['Danish', 'da', 'da_DK'],
		['Spanish', 'es_ES', 'es'],
		['French', 'fr', 'fr'],
		['Russian', 'ru', 'ru'],
		['Czech', 'cs', 'cs'],
		['Afrikaans', 'af', 'af'],
		['Korean', 'ko', 'ko'],
		['Dutch', 'nl', 'nl'],
		['Italian', 'it', 'it'],
		['Polish', 'pl', 'pl']
	]
	

	StringMatches = loadJSON(script_dir, "translation.matches.json")
	transiflex_data_default = loadJSON(PlexWeb_dir, "for_use_plex-web_en-usjson_"+defaultLanguage[1]+".json")
	pfk_data_default = loadJSON(pfkTranslation_dir, "plex_for_kodi_"+defaultLanguage[1]+".json")


	for language in supportedLanguages:
		print("Generating: "+language[0])
	
		transiflex_data = {}
		if language[0] != defaultLanguage[0]:
			transiflex_data = loadJSON(PlexWeb_dir, "for_use_plex-web_en-usjson_"+language[1]+".json")
				
		pfk_data = {}
		if language[0] != defaultLanguage[0]:
			pfk_data = loadJSON(pfkTranslation_dir, "plex_for_kodi_"+language[1]+".json")

		po = setupFile(language[0], language[2])
		po = matchTransiflex(po, StringMatches, transiflex_data, transiflex_data_default)
		po = matchPFK(po, pfk_data, pfk_data_default)
		
		save_dir = language_dir+"/"+language[0]
		
		if not os.path.exists(save_dir):
			os.makedirs(save_dir)

		po.save(save_dir+"/strings.po")
		print("Generated:  "+language[0])
	print("Finished!")
	
def setupFile(language, languageShort):
	po = polib.POFile()
	po.metadata = {
		'INFO': 'THESE FILES ARE AUTOMATICALLY GENERATED, PLEASE DO NOT MODIFY!',
		'Project-Id-Version': 'XBMC-Addons',
		'Report-Msgid-Bugs-To': 'alanwww1@xbmc.org',
		'POT-Creation-Date': 'YYYY-MM-DD 00:00+0100',
		'PO-Revision-Date': 'YYYY-MM-DD 00:00+0100',
		'Last-Translator': 'FULL NAME <EMAIL@ADDRESS>',
		'Language-Team': language,
		'MIME-Version': '1.0',
		'Content-Type': 'text/plain; charset=UTF-8',
		'Content-Transfer-Encoding': '8bit',
		'Language': languageShort,
		'Plural-Forms': 'nplurals=2; plural=(n != 1);'
	}
	return po
	
def matchTransiflex(po, StringMatches, transiflex_data, defaultData):
	for matchSTR, matchIDs in StringMatches.items():
		# Convert String to Array
		if not isinstance(matchIDs, list):
			matchIDs = [matchIDs]

		for matchID in matchIDs:
			if matchSTR in transiflex_data:
				po = poAppend(po, matchID, defaultData[matchSTR], transiflex_data[matchSTR])
			else:
				po = poAppend(po, matchID, defaultData[matchSTR], "")
	return po

def matchPFK(po, pfk_data, defaultData):
	for matchID, matchSTR in pfk_data.items():
		defaultData.pop(matchID, None) #remove element from default data (english language) since we have a real translation
		po = poAppend(po, matchID, defaultData[matchID], matchSTR)
		
	for matchID, matchSTR in defaultData.items():
		po = poAppend(po, matchID, matchSTR, "")
	return po

def loadJSON(dir, filename):
	file = os.path.join(dir, filename)
	if os.path.isfile(file):
		dict = json.load(codecs.open(file, 'r', 'utf-8-sig'))
		#sort by key name to have a better github history
		return collections.OrderedDict(sorted(dict.items()))
	return {}
	
def poAppend(po, msgctxt, msgid, msgstr):
	entry = polib.POEntry(
			msgctxt=msgctxt,
			msgid=msgid,
			msgstr=msgstr
		)
	po.append(entry)
	return po

main()