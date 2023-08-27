from enum import Enum

"""Used to collect analytics. I planned on making graphs and stuff with them but never got around to it. I'm leaving this here in case I ever want to do that."""

class Analytics(Enum):
    CHATBOTLIST = 0
    CHATBOTCREATE = 1
    SETTINGS = 2 
    CHATBOTINFO = 3
    SHOWENABLEDHERE = 4
    ENABLEHERE = 5
    DISABLEHERE = 6
    CHATBOTCLEARMEMORY = 7
    CHATBOTVIEWMEMORY = 8
    CHATBOTSETDEFAULT = 9
    CONVERSE=10
    ADMINROLES=11
    CREDITS=12
    CREDITSVOTE = 13
    CREDITSCLAIM=14
    TIER1CREDITS=15
    TIER2CREDITS=16
    TIER3CREDITS=17
    PROMPT=18
    INCLUDEUSERNAMES=19
    PDFORVIDEO=20
    MENTIONMODE=21
    LONGTERMMEMORY=22
    WEBSEARCH=23
    LONGPROMPT=24
    REGENERATEORCONTINUEBUTTONS=25
    REGENERATE=26
    CONTINUE=27
    AIMODEL=28
    VOTECOMMAND=29
    CLAIMCOMMAND=30
    GOT_GPT_RESPONSE=31
    INJECTMESSAGE = 32
    TEMPERATURE = 33
    PP = 34
    FP = 35
    TOPP = 36
    RAN_OUT_OF_CREDITS = 37
    LOREBOOKS = 38
    
    
    HALF_DAY_IN_SECONDS = 43200