#!/bin/bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
# triggers the daily brief at 7am
echo "Triggering daily brief..."
# Assuming hermes CLI has a way to inject a message into the session
hermes chat --message "Please generate my daily brief. Include today's calendar, top 3 todos, a pre-drafted LinkedIn post, and pending approvals. Act as my Life Organizer."
