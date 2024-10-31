"""
Wrappers for TF functions.
Developed by Milan Straka for the NPFL122 course at MFF CUNI.
"""

import numpy as np


def typed_np_function(*types):
    """Typed NumPy function decorator.

    Can be used to wrap a function expecting NumPy inputs.

    It converts input positional arguments to NumPy arrays of the given types,
    and passes the result through `np.array` before returning (while keeping
    original tuples, lists and dictionaries).
    """
    def check_typed_np_function(wrapped, args):
        if len(types) != len(args):
            while hasattr(wrapped, "__wrapped__"):
                wrapped = wrapped.__wrapped__
            raise AssertionError("The typed_np_function decorator for {} expected {} arguments, but got {}".format(
                wrapped, len(types), len(args)))

    def structural_map(function, value):
        if isinstance(value, tuple):
            return tuple(structural_map(function, element) for element in value)
        if isinstance(value, list):
            return [structural_map(function, element) for element in value]
        if isinstance(value, dict):
            return {key: structural_map(function, element) for key, element in value.items()}
        return function(value)

    class TypedNpFunctionWrapper:
        def __init__(self, func):
            self.__wrapped__ = func

        def __call__(self, *args, **kwargs):
            check_typed_np_function(self.__wrapped__, args)
            return structural_map(np.array, self.__wrapped__(
                *[np.asarray(arg, typ) for arg, typ in zip(args, types)], **kwargs))

        def __get__(self, instance, cls):
            return TypedNpFunctionWrapper(self.__wrapped__.__get__(instance, cls))

    return TypedNpFunctionWrapper


def raw_tf_function(dynamic_dims):
    """Faster but raw `tf.function` implementation.

    All unnecessary steps are shaven off, only the Graph execution is performed.
    Only positional Numpy arguments are supported, the result is either a Numpy
    array or a list of them. Uses TensorFlow internals, so it might not work for you.

    The `dynamic_dims` argument specified the number of "dynamic" (not known statically
    in the computational graph) dimensions of every input. It can be either
    - an integer, in which case it is used for all inputs, or
    - a list, whose elements correspond to the positional arguments of the TF call.
    """
    import weakref

    import tensorflow as tf
    import tensorflow.python.eager as tfe
    import tensorflow.python.framework.constant_op as constant_op

    class RawTFFunctionWrapper:
        def __init__(self, func):
            self.__wrapped__ = func
            self._concrete_function = None
            self._instances = weakref.WeakKeyDictionary()

        def __call__(self, *args):
            if self._concrete_function is None:
                self._concrete_function = tf.function(self.__wrapped__).get_concrete_function(
                    *[tf.TensorSpec((None,) * dynamic + arg.shape[1:], dtype=tf.dtypes.as_dtype(arg.dtype))
                      for arg, dynamic in zip(
                            args, dynamic_dims if isinstance(dynamic_dims, list) else [dynamic_dims] * len(args))])
            ctx = tfe.context.context()
            inputs = [constant_op.convert_to_eager_tensor(np.asarray(arg), ctx) for arg in args]
            result = tfe.execute.execute(self._concrete_function.name, len(self._concrete_function.outputs),
                                         inputs + self._concrete_function.captured_inputs, {}, ctx)
            return result[0] if len(self._concrete_function.outputs) == 1 else result

        def __get__(self, instance, cls):
            wrapper = self._instances.get(instance, None)
            if wrapper is None:
                self._instances[instance] = wrapper = RawTFFunctionWrapper(self.__wrapped__.__get__(instance, cls))
            return wrapper

    return RawTFFunctionWrapper
