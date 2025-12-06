Ruler Intelligence Suite – SRU Edition (Alpha 0.1)

Unofficial Modding & Intelligence Toolkit for Supreme Ruler Ultimate

https://www.youtube.com/watch?v=HUjywlrrUwY  (2030 ver)

The SRU Edition of the Ruler Intelligence Suite is an unofficial memory-reading, analytics, and unit-comparison overlay designed specifically for Supreme Ruler Ultimate.
It brings modern tooling, real-time unit insight, and advanced analysis features to a game where such visibility has traditionally been difficult or impossible.

⚠️ This version is fully adapted for SRU data formats, SRU memory structures, and SRU tech/unit effects.

Features (SRU-Specific)
🔍 Live Unit Comparison (Overlay INS)

Compare up to three units side-by-side, including:

Base stats

Attack/defense values

Movement, spotting, missile capacity

Unit class & category

Effects from researched techs

Works both when:

Selecting a unit on the world map

Opening a unit blueprint dialog
(using two independent SRU memory addresses)

📘 Tech Impact Viewer (SRU Version)

Explore how each SRU technology affects:

Global economic/military parameters

Specific unit classes or individual units

Unlockable units (based on tech requirements)

Search by:

Tech name

Tech ID

Unit name

Unit category

Economic Intelligence Logger (SRU Edition)

A background logger that reads SRU memory values and produces structured logs and analytics.

Tracks:

Treasury

GDP / GDP-C

Inflation

Resources (Oil, Ore, Uranium, etc.)

Domestic Approval & World Opinion

Production & stock levels

Data is exported to CSV and visualized through Python analytics tools:

Daily / weekly / monthly aggregation

Interactive charts

Trendline detection

Export to PNG

Logs are stored inside:

Documents/SRU_Logger/logs/

Mod-Compatible Data Loading

The suite automatically reads SRU-specific data files:

DEFAULT.UNIT

DEFAULT.TTRX

No assets from BG titles are required.

Installation

Download the latest SRU release from GitHub.

Extract the ZIP to a folder of your choice.

Run the exe


Usage
Launching the Tools

The launcher allows you to start:

The overlay

The logger

SRU itself

Paths to your data files are loaded automatically and can be edited manually.

Parameters supported:

--default-unit DEFAULT.UNIT
--default-ttrx DEFAULT.TTRX

🛰️ Real-Time Unit Selection (Overlay)

Press INS to open the overlay.

It automatically detects units using both SRU pointers:

Click unit on the map → pointer A

Open blueprint → pointer B

The tool detects which pointer changed and loads the correct unit.

Mouse bindings:

Left click → Unit B

Right click → Unit C

Middle click → Unit D

Unit B can be locked.

🧬 Tech Application in SRU


Tech Impact Mode (SRU)

Shows:

All units modified by a tech

All units unlocked by a tech

Search and filter by:

Tech

Unit

Category

Logging (SRU)

All logs are timestamped and saved inside:

Documents/SRU_Logger/logs/

Scenarios that do not expose the in-game calendar require manual entry at first launch.

Charts support:

Value overlays

Comparison mode

Export to file

To Do / Help Wanted (SRU Version)

Complete mapping of SRU weapon ranges (soft/hard/naval/sub).

Improve accuracy of tech-to-unit relationships (SRU TTR/TTRX is inconsistent).

Locate SRU’s in-game date pointer for automatic timetable logging.

Add SRU-specific missile data (size, guidance, class).

Add population, debt, and unrest logging.

If you want to contribute, open a PR or submit an Issue.

Legal Notice

This is a third-party, unofficial tool.

It does not include:

Any original SRU game files

DEFAULT.UNIT

DEFAULT.TTRX

Proprietary assets belonging to BattleGoat Studios

Users must provide their own legally-obtained game files.
