# mumble opsdroid

A simple module for interacting with mumble using an opsdroid chat bot. Hopefully when [https://matrix.org](matrix) gets discord-esque PTT chat rooms this will be obsoleted, at least for my purposes.

## Features
1. Monitor and notify upon request or intelligent intervals active user count
2. Send audio clips

### Requirements
* opus
* pymumble

`opus` also requires `ffmpeg` etc. See `Dockerfile` for details how to compile it with Alpine.

### opsdroid skill config
in your opsdroid's `configuration.yaml`

```yaml
  mumble_opsdroid:
    path: /tmp/skills/mumble_opsdroid
    room_notify: "room identifier" # e.g. #!weirdstring:matrix.org see opsdoid docs
    mumble_host: "mumble.your.server"
    mumble_port: 64738
    bot_username: "opsdroid"
    bot_channel: "main" # how you name your mumble channels
```

### skill usage
| command | args | function |
| ----- | ----- | ----- |
| `!mumble` | - | return server details and number of active users |
| `!mumble <clip id> <channel> | audio clip id, channel name | plays audio clip to channel |

e.g. `!mumble 29 Main`
