"""Small local joint/cloth animation for edge and suspended Knight artwork.

The mask and contact anchors stay in place. This is a runtime deformation mesh,
not a rotating rectangle or a change to the source artwork.
"""
import math
from PIL import Image

TRANSFORM = getattr(Image, 'Transform', Image)
RESAMPLE = getattr(Image, 'Resampling', Image)


def joint_offsets(kind, phase, edge=None, profile=None):
    """Return normalized joint centers, radius and pixel travel at 184px high."""
    wave = math.sin(phase * math.tau)
    pulse = math.sin(phase * math.pi) ** 2
    # Hanging poses keep everything above the mask fixed. Only the lower body,
    # free arm, prop and loose cloth articulate beneath that support.
    cloth = (.22, .78, .23, .6*wave, .15*wave)
    if kind == 'micro':
        # Broad weights produce a visible 1–2px cloth/breath movement at the
        # actual desktop size; tiny narrow weights vanished after downscaling.
        joints = [(.19, .79, .38, 2.0*wave, .65*wave),
                  (.81, .81, .34, -1.6*wave, -.45*wave),
                  (.5, .68, .34, 0, -1.35*wave)]
        if profile in ('nail', 'battle', 'work', 'study'):
            joints += [(.68, .7, .23, .8*wave, -.8*wave),
                       (.86, .76, .26, 1.2*wave, -.7*wave)]
        elif profile == 'shell':
            joints += [(.34, .72, .26, .9*wave, -.6*wave),
                       (.66, .72, .26, -.9*wave, -.6*wave)]
        elif profile == 'soul':
            joints += [(.38, .69, .24, .65*wave, -.85*wave),
                       (.62, .69, .24, -.65*wave, -.85*wave)]
        elif profile in ('eat', 'bowl', 'flower'):
            joints += [(.62, .71, .25, -.55*wave, -.8*wave)]
        elif profile in ('explore', 'notes', 'read', 'review', 'organize'):
            joints += [(.63, .76, .24, .9*wave, -.5*wave)]
        elif profile == 'drag':
            joints += [(.36, .87, .22, .75*wave, .65*wave),
                       (.65, .87, .22, -.75*wave, -.65*wave)]
        elif profile == 'sleep':
            joints += [(.5, .76, .34, 0, -.8*wave)]
        return joints
    if kind == 'sleep':
        return [(.46, .78, .27, 0, -.65*wave)]
    if kind == 'eat' or kind == 'bowl':
        return [(.58, .61, .12, -1.7*pulse, -3.8*pulse), cloth]
    if kind in ('nail', 'battle', 'work', 'study'):
        # Three-part wrist gesture: draw back, short cut, recover, then pause.
        t = phase * 4
        stroke = (-math.sin(t*math.pi) if t < 1 else
                  1.6*math.sin((t-1)*math.pi) if t < 2 else 0)
        if kind == 'nail' and edge == 'top':
            return [(.4, .64, .19, -1.2*stroke, -1.8*stroke),
                    (.17, .81, .24, -1.8*stroke, -3.6*stroke), cloth]
        return [(.68, .7, .2, 2.*stroke, -2.8*stroke),
                (.88, .74, .22, 2.7*stroke, -4.2*stroke), cloth]
    if kind == 'shell':
        return [(.34, .65, .18, 1.9*pulse, -1.4*pulse),
                (.66, .66, .18, -1.9*pulse, -1.4*pulse),
                (.48, .88, .2, 0, -1.*pulse)]
    if kind == 'soul':
        return [(.36, .68, .18, 1.5*pulse, -.7*pulse),
                (.64, .68, .18, -1.5*pulse, -.7*pulse), cloth]
    if kind == 'flower':
        return [(.65, .66, .18, -.65*pulse, -1.3*pulse), cloth]
    if kind in ('explore', 'notes', 'read', 'review', 'organize'):
        return [(.62, .72, .15, 2.*wave, -.65*pulse),
                (.73, .8, .22, .55*wave, 0), cloth]
    if kind == 'drag':
        return [(.3, .65, .18, -1.2*wave, .6*wave),
                (.7, .65, .18, 1.2*wave, -.6*wave),
                (.36, .89, .16, .8*wave, 1.7*wave),
                (.65, .89, .16, -.8*wave, -1.7*wave), cloth]
    if kind in ('relax', 'sit'):
        return [(.76, .87, .18, 1.1*pulse, -1.8*pulse), cloth]
    if kind == 'look':
        return [(.64, .56, .15, -.7*pulse, -1.6*pulse), cloth]
    return [(.49, .4, .18, .55*wave, 0), cloth]


def deform(image, kind, phase, edge=None, profile=None):
    width, height = image.size
    joints = joint_offsets(kind, phase, edge, profile)
    strength = min(1., height/184.)
    # Right-edge sprites have already been mirrored by the frame loader.
    mirrored = edge == 'right'

    def source_point(x, y):
        u, v = x/width, y/height
        if mirrored:
            u = 1-u
        dx = dy = 0.
        for cx, cy, radius, vx, vy in joints:
            distance = ((u-cx)**2 + (v-cy)**2) / radius**2
            weight = math.exp(-distance*2.8)
            dx += vx*weight
            dy += vy*weight
        # Freeze top grip line and all screen-contact borders, avoiding sliding.
        margin = min(1., x/9., (width-x)/9., y/9., (height-y)/9.)
        if edge == 'top':
            margin *= min(1., max(0., (v-.25)/.2))
        if kind == 'micro':
            margin *= min(1., max(0., (v-.5)/.12))
        return (x + (-dx if mirrored else dx)*strength*margin,
                y + dy*strength*margin)

    mesh = []
    step = 10
    for top in range(0, height, step):
        bottom = min(height, top+step)
        for left in range(0, width, step):
            right = min(width, left+step)
            quad = source_point(left, top) + source_point(left, bottom) + source_point(right, bottom) + source_point(right, top)
            mesh.append(((left, top, right, bottom), quad))
    # Premultiplied interpolation avoids colored fringes around transparency.
    result = image.convert('RGBa').transform(image.size, TRANSFORM.MESH, mesh,
                                           resample=RESAMPLE.BICUBIC).convert('RGBA')
    # Mesh interpolation can otherwise shift the last edge pixel by a fraction
    # even when its vertex is fixed. Keep contact strips exactly unchanged.
    for box in ((0, 0, width, 2), (0, height-2, width, height),
                (0, 0, 2, height), (width-2, 0, width, height)):
        result.paste(image.crop(box), box[:2])
    return result
