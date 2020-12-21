# KH Re:COM Tools

A set of experimental tools for researching Kingdom Hearts Re:Chain of Memories for the PlayStation 2.

## Extractor

Extracts all files from a KH Re:COM disk image (.ISO). Supports both NA and JP releases.

Sample usage:

```khrecom-ps2-extractor.exe C:\path\to\game.iso -d C:\optional\extract\dir```

The default location for extracted files will be a folder named `extract/` in the working directory.

## Resource Unpacker

Extracts files from packed resource file types. To find these files, run the above extractor on the .ISO first. Supported extensions are:

* .ABC, .BIN, .ESD, .EPD, .GSD, .PTD
* .CAP (Camera Data)
* .CTD (Cutscene Data)
* .EFF (Particle Effects)
* .RTM, .VTM (TIM2 Images/Textures)
* .SPR (Sprites)
* .TXA (Animated Textures)
* .SND, .RSD, .VSM (Sound Bank)

Sample usage:

```khrecom-ps2-rsrc-unpacker.exe C:\path\to\resou.rce -d C:\optional\extract\dir```

By default, the unpacker will create a new folder in the working directory with the same name as the original file.
