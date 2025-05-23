'''
######################################################################
#
#   opsdroid mumble module
#
#   monitors user count and provides non-noisey updates to a channel
#   ability to send audio to a channel
#
######################################################################
'''
import datetime
import os
from asyncio import sleep
from random import choice, randint
from copy import deepcopy
import requests
import humanize

from aiohttp.web import Request
from opsdroid.skill import Skill
from opsdroid.matchers import match_regex, match_crontab, match_event, match_always
from opsdroid.events import Message
import pymumble_py3 as pymumble
from pymumble_py3.constants import *

class MumbleSkill(Skill):
    '''
    opsdroid module for mumble. notifies on user prescence and allows sending
    audio clips to a channel
    '''
    def __init__(self, *args, **kwargs):
        super(MumbleSkill, self).__init__(*args, **kwargs)
        self.bot_was_last_message = False
        self.last_update = datetime.datetime.today() - datetime.timedelta(days=1)
        self.link = self.config.get('mumble_link')
        self.mumble_cli = pymumble.Mumble(
            self.config.get('mumble_host'),
            self.config.get('bot_username'),
            port=self.config.get('mumble_port'),
            password=self.config.get('mumble_password'),
            reconnect=True,
        )
        self.mumble_cli.callbacks.set_callback(
            PYMUMBLE_CLBK_CONNECTED, self.mumble_init
        )
        self.bot_channel = None
        self.bot_channel_id = None
        self.users_state = None
        self.mumble_cli.start()
        self.mumble_cli.is_ready()
        self.mumble_init()

    def mumble_init(self):
        '''
        starts mumble client and moves to bot_channel
        '''
        channel_name = self.config.get('bot_channel')
        self.bot_channel_id = self.mumble_cli.channels.find_by_name(channel_name)['channel_id']
        self.bot_channel = self.mumble_cli.channels[self.bot_channel_id]
        self.bot_channel.move_in()
        self.users_state = self.get_users_state()

    #############################################
    #
    #   0. Avoid spamming
    #       The bot notifies if a stream is ongoing every hour
    #       if no one posts within that hour, it is superfluous;
    #       this functionality prevents that.
    #
    #############################################

    async def avoid_spam_send(self, msg):
        '''
        Takes account if the bot sent the last event
        prior to sending
        '''
        if not self.bot_was_last_message:
            await self.opsdroid.send(
                Message(
                    text=msg,
                    target=self.config.get('room_notify')
                )
            )
            self.bot_was_last_message = True
        else:
            pass

    @match_always
    async def who_last_said(self, event):
        '''
        required to know who sent the last message
        '''
        if hasattr(event, 'target') and event.target == self.config.get('room_notify'):
            self.bot_was_last_message = False

    #############################################
    #
    #   1. Core functionality
    #
    #############################################

    def get_users_state(self):
        '''
        returns number of active users.
        discludes both suppressed and deafened users
        '''
        users_state = {
            'active_users'  :0,
            'deafened_users':0,
            'suppressed_users':0
        }
        for user_id in self.mumble_cli.users:
            user = self.mumble_cli.users[user_id]
            # check for human user. bots tend not to have 'hash'
            if 'hash' in user:
                if 'self_deaf' in user and user['self_deaf']:
                    users_state['deafened_users'] += 1
                elif 'suppress' in user and user['suppress']:
                    users_state['suppressed_users'] += 1
                else:
                    users_state['active_users'] += 1

        return users_state

    async def report_users_state(self, target=None):
        '''
        Send a string to a target room with the server location
        and active users. defaults to room_notify config var
        '''
        text = (
            f'🗣️ <a href=\"{self.link}\">Mumble</a> 📚 Active Users: {self.get_users_state()["active_users"]}'
        )

        if not target:
            await self.avoid_spam_send(text)
            self.last_update = datetime.datetime.today()
        else:
            await self.opsdroid.send(
                Message(
                    text=text,
                    target=target
                )
            )

    async def send_audio(self, audio_clip_id=None, channel_name=None):
        '''
        send an audio clip to a channel.
        bot channel by default.
        must be pcm format
        ffmpeg -i input.wav -f s16le -acodec pcm_s16le -ac 1 -ar 48000 output.pcm
        '''
        if channel_name:
            try:
                channel_id = self.mumble_cli.channels.find_by_name(channel_name)['channel_id']
            except pymumble.errors.UnknownChannelError:
                return
        else:
            channel_id = self.bot_channel_id

        if audio_clip_id:
            sound_path = os.path.join(os.path.dirname(__file__), f'./sfx/{audio_clip_id}.pcm')
        else:
            sound_path = os.path.join(os.path.dirname(__file__), './sfx/29.pcm')
        if not os.path.exists(sound_path):
            return
        with open(sound_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        self.mumble_cli.sound_output.add_sound(audio_data)
        self.mumble_cli.sound_output.set_whisper(channel_id, channel=channel_id)

    #############################################
    #
    #   2. Automatic actions
    #
    #############################################

    @match_crontab('*/15 * * * *')
    async def mumble_monitor(self, event):
        '''
        monitor mumble population and infrequently post to main room
        '''
        old_user_state = deepcopy(self.users_state)
        tmp_users_state = self.get_users_state()


        active_users = tmp_users_state['active_users'] > 1
        if not active_users:
            self.users_state = tmp_users_state
            return

        time_since_last = datetime.datetime.today() - self.last_update

        more_users_soon = tmp_users_state['active_users'] > old_user_state['active_users']
        time_to_remind = time_since_last > datetime.timedelta(hours=1)

        stability_check = (more_users_soon or time_to_remind)

        if (not stability_check) or time_since_last < datetime.timedelta(minutes=15):
            return

        stability_stats = []
        for _ in range(5):
            await sleep(60)
            old_user_state = deepcopy(tmp_users_state)
            tmp_users_state = self.get_users_state()
            active = tmp_users_state['active_users'] > 1
            active &= tmp_users_state['active_users'] >= old_user_state['active_users']
            stability_stats.append(active)

        update = stability_stats[4] and stability_stats.count(True) > 3

        if update:
            await self.report_users_state()

        self.users_state = self.get_users_state()

    @match_crontab('0 */6 * * *')
    async def periodic_audio_send(self, event):
        '''
        periodically send audio clips
        One clip randomly ever quarter of the day
        '''
        await sleep(60 * 60 * randint(1, 6))
        await self.send_audio(audio_clip_id='29')

    @match_crontab('* * * * *')
    async def health_check(self, event):
        '''
        Check if in server or not
        '''
        if self.mumble_cli.connected == PYMUMBLE_CONN_STATE_NOT_CONNECTED:
            self.mumble_cli.is_ready()
            self.mumble_cli.start()
            self.mumble_init()

    #############################################
    #
    #   3. Chat-callable commands
    #
    #############################################

    @match_regex('^!mumble$')
    async def command_mumble_info(self, event):
        '''
        returns server info and usercount (not including bot)
        Example:
            !mumble
        '''
        await self.report_users_state(target=event.target)

    @match_regex(r'^!mumble (?P<audio_clip_id>(\w{0,}\d{1,3})) ?(?P<channel_name>(.+)$)?')
    async def command_send(self, event):
        '''
        command to send audio files
        audio_clip_id is an in from {1,...,999}. plays e.g. 29.pcm
        channel_name could be "Main" or "Lobby"
        Example:
            !mumble 29 Main
        '''
        await self.send_audio(
            audio_clip_id=event.entities['audio_clip_id']['value'],
            channel_name=event.entities['channel_name']['value']
        )

    @match_regex(r'^!help mumble$')
    async def help_mumble(self, event):
        '''
        Give user back text on certain commands
        '''
        text = 'Usage:<br>'
        text += '<b>!mumble</b> | Checks current status and gives a link for setup<br>'
        text += '<b>!mumble [n] [optional: channel]</b> | Send voice clip n - optionally specify a channel'

        await self.opsdroid.send(
            Message(
                text=text,
                target=event.target
            )
        )

