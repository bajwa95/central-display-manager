# Photo Frame Launcher

A centralized digital signage and slideshow system for managing multiple Raspberry Pi or browser-based displays from a single Flask server.

Photo Frame Launcher is designed for dedicated screens running Chromium in kiosk mode. Each display connects to a department or screen-specific URL and automatically receives its assigned images and videos from the central server.

The system includes automatic media updates, configurable image display times, video playback, display heartbeat monitoring, current-media reporting, online/offline status, and remote display refresh controls.

---

## Features

### Centralized Display Server

A single Flask + Flask-SocketIO server manages all connected displays.

Display folders are discovered automatically from the configured parent media directory. Each folder becomes its own display endpoint.

Example:

```text
__SCREENS__/
├── Lobby/
├── LunchRoom/
├── MeetingRoom/
├── Reception/
└── LargeFormatDisplay/
```

These folders automatically become URLs such as:

```text
/Lobby
/LunchRoom
/MeetingRoom
/Reception
/LargeFormatDisplay
```

This makes it easy to add additional displays without hard-coding every screen into the application.

---

## Raspberry Pi / Browser Display Clients

Each physical display can use a Raspberry Pi running Chromium in kiosk mode.

For example, the Lobby Raspberry Pi loads:

```text
http://SERVER/Lobby
```

while another Raspberry Pi could load:

```text
http://SERVER/Reception
```

The browser itself acts as the display client. No separate monitoring application is required on the Raspberry Pi for slideshow status reporting.

---

## Automatic Image and Video Slideshow

Each display automatically loads supported media from its assigned folder.

Supported media currently includes:

```text
.png
.jpg
.jpeg
.gif
.mp4
```

Images and videos can be added or removed from the server without manually rebuilding the slideshow.

---

## Configurable Image Display Time

Image display duration can be controlled directly through the filename.

The number before the first `-` represents how many seconds the image should remain on screen.

Example:

```text
5-SafetyNotice.jpg
```

Displays for:

```text
5 seconds
```

Example:

```text
30-ProductionTarget.jpg
```

Displays for:

```text
30 seconds
```

Example:

```text
120-CompanyAnnouncement.jpg
```

Displays for:

```text
120 seconds
```

### Default Display Time

If no numeric time prefix exists, the image uses the default slideshow duration.

For example:

```text
Welcome.jpg
```

currently displays for:

```text
10 seconds
```

This allows simple media files to work immediately while still providing per-image timing control when required.

---

## Media Ordering

The slideshow supports numeric timing prefixes without requiring the timing value to determine the media's alphabetical ordering.

For example:

```text
30-openhouse.jpg
10-safety.jpg
60-welcome.jpg
```

The server extracts the filename portion after the numeric prefix when sorting the media.

This allows the number prefix to primarily control display duration.

---

## Video Playback

MP4 video files can be included alongside slideshow images.

Videos:

- Play automatically
- Run muted for reliable Chromium kiosk autoplay
- Use inline playback
- Automatically advance when playback finishes
- Use the video's actual duration when available
- Include fallback/watchdog handling if playback fails
- Skip problematic videos instead of permanently stopping the slideshow

This is especially useful for unattended Raspberry Pi displays where one damaged or incompatible video should not stop the entire screen.

---

## Video Playback Watchdog

The browser monitors video playback for common failure conditions.

The slideshow can automatically move forward if:

- A video fails to load
- Video decoding fails
- Playback stalls
- Playback is aborted
- Browser autoplay fails
- Video metadata cannot be used normally

This helps keep unattended displays running continuously.

---

## Automatic Folder Monitoring

The server uses Watchdog to monitor every display media folder.

When media is:

- Added
- Removed
- Modified

the server automatically rebuilds the media list and sends an update through Socket.IO.

This means administrators can update signage simply by changing files in the appropriate display folder.

---

## Live Socket.IO Updates

Flask-SocketIO provides real-time communication between the central server and connected displays.

It is used for:

- Media update notifications
- Display registration
- Heartbeats
- Current-media reporting
- Remote refresh commands
- Display-specific Socket.IO rooms

This avoids requiring each display to constantly reload the entire application.

---

# Central Display Manager

The project includes a browser-based management dashboard:

```text
/displays
```

The dashboard provides a centralized view of all configured screens.

Example:

```text
Lobby
🟢 Online

Current Media
test_02.jpg

Last seen: 4 sec ago

[View] [Refresh]
```

---

## Online / Offline Monitoring

Every display periodically sends a heartbeat to the server.

The heartbeat contains information including:

```text
Screen name
Current media
Connection/session information
Last heartbeat time
```

The server determines display health from the heartbeat rather than relying only on browser disconnect events.

Current status thresholds are:

```text
Less than 30 seconds     🟢 Online
30–90 seconds            🟡 Stale
More than 90 seconds     🔴 Offline
```

This makes monitoring more reliable if a Raspberry Pi freezes, Wi-Fi disappears, Chromium crashes, or a device loses power without cleanly disconnecting.

---

## Heartbeat Interval

Connected displays currently send a heartbeat approximately every:

```text
10 seconds
```

When the displayed media changes, the client also sends an immediate heartbeat so the dashboard can report the new filename without waiting for the next regular heartbeat.

---

## Current Media Reporting

Each screen reports the media file currently being displayed.

For example:

```text
Lobby
🟢 Online

Current Media:
30-Safety_Update.jpg
```

As the slideshow advances, the reported media changes automatically.

This makes it possible to confirm remotely what content a screen should currently be showing.

---

## Display Status API

Display status can also be accessed as JSON:

```text
/api/displays
```

Example response:

```json
{
    "Lobby": {
        "current_media": "test_02.jpg",
        "last_seen_seconds": 4.5,
        "status": "online"
    },
    "Reception": {
        "current_media": null,
        "last_seen_seconds": null,
        "status": "offline"
    }
}
```

This endpoint can also be used for future integrations or monitoring tools.

---

## Individual Display Refresh

Each connected display joins its own Socket.IO room.

For example:

```text
display:Lobby
display:Reception
display:LunchRoom
```

The Display Manager can therefore remotely refresh one screen without affecting the others.

Example:

```text
Lobby → Refresh
```

refreshes only the Lobby display.

This is useful when troubleshooting a screen or forcing it to reload newly deployed content.

---

## Refresh All Displays

The management dashboard also provides:

```text
Refresh All Displays
```

This broadcasts a refresh command to all connected screens.

A confirmation prompt is displayed before the command is sent.

---

## View Display

The management dashboard provides a **View** button for every screen.

This opens the actual slideshow URL in another browser tab, allowing an administrator to preview exactly what that display is serving.

---

# Production Toolkit Integration

The Display Manager is integrated with the existing Production Toolkit homepage.

The Display Screens section provides two options:

```text
Manage Displays
Open Display
```

**Manage Displays** opens the central management dashboard.

**Open Display** allows an individual display to be selected and viewed directly.

---

# Offline-Friendly Design

Once the server and local network are running, the signage system does not depend on a cloud-hosted signage platform.

Media is served from the organization's own central media storage and Flask server.

This provides:

- Central control
- Local network operation
- No per-screen cloud subscription
- Simple media deployment
- Easy Raspberry Pi expansion

---

# Typical Architecture

```text
                    Central Server
                         │
                 Flask + Socket.IO
                         │
              Watchdog Media Monitoring
                         │
          ┌──────────────┼──────────────┐
          │              │              │
       /Lobby       /LunchRoom      /Reception
          │              │              │
          ▼              ▼              ▼
    Raspberry Pi    Raspberry Pi    Raspberry Pi
      Chromium        Chromium        Chromium
       Kiosk           Kiosk           Kiosk
          │              │              │
          └──────── Heartbeats ─────────┘
                         │
                         ▼
                 Display Manager
                    /displays
```

---

# Typical Display Workflow

### 1. Add Media

Place an image or video inside the desired display folder.

Example:

```text
Lobby/
└── 30-Welcome.jpg
```

### 2. Server Detects the Change

Watchdog detects the new file and updates the Lobby media list.

### 3. Display Receives the Update

Socket.IO notifies the connected Lobby display.

### 4. Slideshow Updates

The browser updates its slideshow.

### 5. Display Reports Current Media

The browser reports:

```text
current_media = 30-Welcome.jpg
```

### 6. Dashboard Updates

The Display Manager shows the screen's connection status, current media, and heartbeat age.

---

# Example Media Folder

```text
Lobby/
├── background.jpg
├── 10-Welcome.jpg
├── 30-Safety_Update.jpg
├── 60-Company_News.jpg
├── Announcement.jpg
└── Production_Update.mp4
```

In this example:

```text
10-Welcome.jpg
```

is displayed for 10 seconds.

```text
30-Safety_Update.jpg
```

is displayed for 30 seconds.

```text
60-Company_News.jpg
```

is displayed for 60 seconds.

```text
Announcement.jpg
```

uses the default 10-second duration.

The MP4 plays according to its video duration.

`background.jpg` is reserved as the display background and is excluded from the normal slideshow media list.

---

# Current Display Manager Features

- 🟢 Online display indication
- 🟡 Stale display indication
- 🔴 Offline display indication
- Current media filename
- Last heartbeat age
- Automatic status updates
- Manual status refresh
- Individual display viewing
- Individual remote display refresh
- Refresh all displays
- Automatic display discovery from folders
- Screen-specific Socket.IO rooms
- Browser heartbeat reporting

---

# Reliability Features

The project includes several features intended for unattended signage operation:

- Automatic Socket.IO reconnection
- Browser heartbeat monitoring
- Server-side online/offline determination
- Video playback watchdog
- Video error recovery
- Automatic slideshow continuation
- Automatic folder change detection
- Automatic media-list updates
- Remote browser refresh
- Raspberry Pi Chromium kiosk compatibility
- Muted video autoplay for reliable kiosk playback

---

# Main Components

```text
srvrauto.py
```

Central Flask/Socket.IO server responsible for media discovery, APIs, display communication, folder monitoring, and remote control.

```text
templates/index.html
```

Display-side slideshow client responsible for image/video playback, timing, Socket.IO communication, heartbeat reporting, and current-media reporting.

```text
templates/displays.html
```

Central Display Manager dashboard.

```text
templates/main2.html
```

Production Toolkit homepage and entry point to the display system.

```text
HybridServerGUI.py
```

Desktop server-control interface used to start, stop, restart, and monitor the Flask/Socket.IO server.

---

# Planned Improvements

Possible future additions include:

- Instant dashboard status events through Socket.IO
- Raspberry Pi hostname reporting
- Device IP reporting
- Raspberry Pi uptime
- CPU temperature monitoring
- Wi-Fi signal monitoring
- Disk-space monitoring
- Remote next-slide command
- Pause/resume slideshow
- Remote reboot
- Remote Chromium restart
- Screenshot/preview reporting
- Display configuration page
- Administrative authentication
- Improved installation/setup tools for new Raspberry Pi displays

---

# Technology

The project uses:

- Python
- Flask
- Flask-SocketIO
- Watchdog
- JavaScript
- Socket.IO
- HTML/CSS
- Bootstrap
- Chromium kiosk mode
- Raspberry Pi

---

# Project Goal

The goal of Photo Frame Launcher is to provide a lightweight, locally controlled digital signage platform that can manage multiple dedicated displays without requiring commercial cloud signage software.

The system is designed around a simple idea:

> Add media to a folder, and the correct screen should update automatically.

At the same time, the central management dashboard provides visibility into whether each display is online, what it is currently showing, and the ability to remotely refresh individual screens when needed.