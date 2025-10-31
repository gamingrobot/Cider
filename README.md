# Cider

Line Art render based on [Malt](https://github.com/bnpr/Malt)

This is a stop-gap solution until the [NPR Project](https://code.blender.org/2025/05/npr-project/) is finished.

Cider renders a separate image output to be composited on-top of an EEVEE or Cycles render. It provides a viewport preview overlay and ability to specify a custom Render Pipeline. For more advanced rendering Malt is still recommended. 

[Documentation](cider-docs/README.md)

## Limitations

- Currently only renders the active ViewLayer
- Compositor nodes need to be setup manually
- Doesn't work with "Mark Freestyle Edge/Face"

## Requirements

- OpenGL 4.5
- Latest Blender stable release.
- Windows or Linux

> A dedicated Nvidia or AMD graphics card is highly recommended.  
