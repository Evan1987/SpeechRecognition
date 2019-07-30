"""Contains DeepSpeech2 model."""

import sys
import os
import logging
import tensorflow as tf
from deep_speech2.model_utils.network import DeepSpeech2
from deep_speech2.decoders.scorer_deprecated import Scorer
from deep_speech2.decoders.decoders_deprecated import ctc_greedy_decoder
from deep_speech2.model_utils.metrics import word_error, char_error
from typing import Union, Optional, Callable, List, Dict


def compute_length_after_conv(max_time_steps, ctc_time_steps, input_length) -> tf.Tensor:
    """
    Computes the time_steps/ctc_input_length after convolution.

    Suppose that the original feature contains two parts:
    1) Real spectrogram signals, spanning input_length steps.
    2) Padded part with all 0s.
    The total length of those two parts is denoted as max_time_steps, which is the padded length of the current batch.
    After convolution layers, the time steps of a spectrogram feature will be decreased.
    As we know the percentage of its original length within the entire length, we can compute the time steps
    for the signal after convolution as follows (using ctc_input_length to denote):
      `ctc_input_length` = (`input_length` / `max_time_steps`) * `output_length_of_conv`.
    This length is then fed into ctc loss function to compute loss.

    :param max_time_steps: max_time_steps for the batch, after padding.
    :param ctc_time_steps: number of timesteps after convolution.
    :param input_length: actual length of the original spectrogram, without padding.
    :return: the ctc_input_length after convolution layer.
    """
    return tf.to_int32(tf.floordiv(
        tf.to_float(tf.multiply(input_length, ctc_time_steps)), tf.to_float(max_time_steps)))


def ctc_loss(label_length: tf.Tensor, ctc_input_length, labels, logits):
    """Computes the ctc loss for the current batch of predictions."""
    label_length = tf.to_int32(tf.squeeze(label_length))
    ctc_input_length = tf.to_int32(tf.squeeze(ctc_input_length))
    sparse_labels = tf.to_int32(tf.keras.backend.ctc_label_dense_to_sparse(labels, label_length))
    y_pred = tf.log(tf.transpose(logits, perm=[1, 0, 2]) + tf.keras.backend.epsilon())

    return tf.expand_dims(
        tf.nn.ctc_loss(labels=sparse_labels, inputs=y_pred, sequence_length=ctc_input_length),
        axis=1)


def evaluate_model(estimator: tf.estimator.Estimator, blank_index: int,
                   transcripts: List[List[int]], input_fn_eval: Callable):
    """
    Evaluate the model performance using WER anc CER as metrics.

    WER: Word Error Rate
    CER: Character Error Rate

    :param estimator: estimator to evaluate.
    :param blank_index: The index indicating the blank.
    :param transcripts: a list of true labels tokenized.
    :param input_fn_eval: data input function for evaluation.
    :return: Evaluation result containing 'wer' and 'cer' as two metrics.
    """
    # Get predictions
    predictions = estimator.predict(input_fn=input_fn_eval)

    # Get probabilities of each pred
    probs = [pred["probabilities"] for pred in predictions]

    n = len(probs)

    total_wer, total_cer = 0., 0.
    for i in range(n):
        decode = ctc_greedy_decoder(probs_seq=probs[i], blank_index=blank_index, vocabulary=None)
        target = transcripts[i]
        decode = "".join([chr(x) for x in decode])
        total_wer += word_error(decode, target)





