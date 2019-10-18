import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
import math

from tensorflow.keras.preprocessing.image import apply_affine_transform as affine

def radon(image, theta=None, circle=True, *, preserve_range=None):
    """
    Calculates the radon transform of an image given specified
    projection angles.
    
    Parameters
    ----------
    image : array_like
        Input image. The rotation axis will be located in the pixel with
        indices ``(image.shape[0] // 2, image.shape[1] // 2)``.
    theta : array_like, optional
        Projection angles (in degrees). If `None`, the value is set to
        np.arange(180).
    circle : boolean, optional
        Assume image is zero outside the inscribed circle, making the
        width of each projection (the first dimension of the sinogram)
        equal to ``min(image.shape)``.
    preserve_range : bool, optional
        Whether to keep the original range of values. Otherwise, the input
        image is converted according to the conventions of `img_as_float`.
        Also see https://scikit-image.org/docs/dev/user_guide/data_types.html
    Returns
    -------
    radon_image : array
        Radon transform (sinogram).  The tomography rotation axis will lie
        at the pixel index ``radon_image.shape[0] // 2`` along the 0th
        dimension of ``radon_image``. This is a 3D array with the single
        grayscale channel on the third axis.
    """
    if image.dtype != tf.uint32:
        image = tf.cast(image, tf.uint8)
    
    if len(image.shape) > 2:
        image = tf.image.rgb_to_grayscale(image)
    
    if theta is None:
        theta = tf.range(180)
    
    if circle:
        img_shape = image.shape[:2]
        shape_min = tf.math.reduce_min(img_shape)
        radius = tf.math.floordiv(shape_min, 2)
        x, y = tf.meshgrid(range(0, img_shape[0]), range(0, img_shape[1]))
        center_x, center_y = tf.math.floordiv(img_shape, 2)
        dist = (x - center_x) ** 2 + (y - center_y) ** 2
        outside_reconstruction_circle = dist > radius ** 2
        if tf.math.reduce_any(image[outside_reconstruction_circle] != 0):
            print('Radon transform: image must be zero outside the '
                'reconstruction circle')
        # Crop image to make it square
        slices = tuple(
            slice(int(tf.math.ceil(excess / 2).numpy()),
                int(tf.math.ceil(excess / 2) + shape_min).numpy())
            if excess > 0 else
            slice(None)
            for excess in (img_shape - shape_min)
        )
        padded_image = image[slices]
    else:
        diagonal = tf.math.sqrt(2) * max(image.shape)
        pad = [int(tf.math.ceil(diagonal - s)) for s in image.shape]
        new_center = [tf.math.floordiv(s + p, 2) for s, p in zip(image.shape, pad)]
        old_center = [s // 2 for s in image.shape]
        pad_before = [nc - oc for oc, nc in zip(old_center, new_center)]
        pad_width = [(pb, p - pb) for pb, p in zip(pad_before, pad)]
        padded_image = tf.pad(image, pad_width, mode='constant',
            constant_values=0)
    # padded_image is always square
    if padded_image.shape[0] != padded_image.shape[1]:
        raise ValueError('padded_image must be a square')
    center = tf.cast(tf.math.floordiv(padded_image.shape[0], 2), tf.float32)
    
    result = []
    image = tf.cast(padded_image, tf.int64).numpy()
    for i, angle in enumerate(theta):
        result.append(tf.math.reduce_sum(affine(image, theta=angle), 0))
    result = tf.stack(result, 0)
    result = tf.transpose(result, [1, 0, 2])
    return result