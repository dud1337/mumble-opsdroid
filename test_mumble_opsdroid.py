"""Unit tests for mumble opsdroid module"""
import logging

import pytest
import opsdroid
import gettext
from opsdroid.testing import *
from  . import MumbleSkill
import pymumble_py3

#@pytest.fixture
#def opsdroid():
#    '''Returns an opsdroid instance'''
#    return OpsDroid(config={})
gettext.install("opsdroid")
_LOGGER = logging.getLogger("opsdroid")

@pytest.fixture
def valid_config():
    '''Returns opsdroid with a test config'''
    config = {
        "connectors":{'shell':{'bot-name':'opsdroid_test'}},
        "skills":{"mumble_opsdroid":{
            'path':         '.',
            'room_notify':  '.',
            'mumble_host':  'mumble.138.io',
            'mumble_port':  64738,
            'bot_username': 'opsdroid_test',
            'bot_channel': 'BBB'
        }}
    }
    return config

@pytest.mark.asyncio
async def test_load_bad_config(opsdroid, valid_config):
    """
    Check bad config - unknown channel
    """
    opsdroid.config["connectors"] = valid_config["connectors"]
    opsdroid.config["skills"] = {"mumble_opsdroid":{"mumble_host":None}}

    with pytest.raises(pymumble_py3.errors.UnknownChannelError):
        await opsdroid.load()

@pytest.mark.asyncio
async def test_check_alive(opsdroid, valid_config):
    """
    Test loading valid config and aliveness
    """
    opsdroid.config["connectors"] = valid_config["connectors"]
    opsdroid.config["skills"] = valid_config["skills"]

    await opsdroid.load()
    skill_class = opsdroid.skills[0].__wrapped__.__self__
    assert skill_class.mumble_cli.is_alive()
    await opsdroid.unload()

@pytest.mark.asyncio
async def test_(opsdroid, valid_config):
    """
    Test load valid config
    """
    opsdroid.config["connectors"] = valid_config["connectors"]
    opsdroid.config["skills"] = valid_config["skills"]

    await opsdroid.load()

    skill_class = opsdroid.skills[0].__wrapped__.__self__
    assert skill_class.mumble_cli.is_alive()
    await opsdroid.unload()

