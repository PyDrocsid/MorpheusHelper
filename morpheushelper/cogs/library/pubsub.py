from PyDrocsid.pubsub import PubSubChannel

send_to_changelog = PubSubChannel()
send_alert = PubSubChannel()
log_auto_kick = PubSubChannel()
get_ulog_entries = PubSubChannel()
