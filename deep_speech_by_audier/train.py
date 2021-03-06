
import os
from tensorflow.python.keras.callbacks import ModelCheckpoint, TensorBoard
from tensorflow.python.keras import backend as K
from deep_speech_by_audier.constant import make_pny_vocab, DATA_SOURCE_DIR, AM_LOG_DIR, AM_MODEL_DIR
from deep_speech_by_audier.input_data import DataGenerator
from deep_speech_by_audier.model.speech import AcousticModel
from deep_speech_by_audier.model.utils import get_session
from evan_utils.utensorflow import get_board_log_path
from typing import Dict
import tensorflow as tf


K.clear_session()
PNY2ID: Dict[str, int] = make_pny_vocab()
ID2PNY: Dict[int, str] = {id_: pny for pny, id_ in PNY2ID.items()}
SHUFFLE = True
FEATURE_TYPE = "fbank"
N_FEATURES = 200
BATCH_SIZE = 4
VOCAB_SIZE = len(PNY2ID)  # 1585
LEARNING_RATE = 8e-4
N_EPOCH = 100
MODEL_TYPE = "DFCNN"
DATA_SOURCE = os.path.join(DATA_SOURCE_DIR, "labeled_data.txt")


TRAIN_BATCH = DataGenerator(
    data_source=DATA_SOURCE, pinyin_sep="-", data_type="train", feed_model="speech", model_type=MODEL_TYPE,
    feature_type=FEATURE_TYPE, n_features=N_FEATURES, shuffle=SHUFFLE, batch_size=BATCH_SIZE, data_length=-1,
    am_vocab=PNY2ID
)

DEV_BATCH = DataGenerator(
    data_source=DATA_SOURCE, pinyin_sep="-", data_type="dev", feed_model="speech", model_type=MODEL_TYPE,
    feature_type=FEATURE_TYPE, n_features=N_FEATURES, shuffle=SHUFFLE, batch_size=BATCH_SIZE, data_length=-1,
    am_vocab=PNY2ID
)

BATCH_NUM = len(TRAIN_BATCH)


if __name__ == "__main__":
    # print("AM_LOG_PATH: %s" % AM_LOG_DIR)
    tf.reset_default_graph()
    model = AcousticModel(vocab_size=VOCAB_SIZE, n_features=N_FEATURES, gpu_num=1,
                          inference_model_type=MODEL_TYPE, learning_rate=LEARNING_RATE, is_training=True)
    model.inference_model.summary()
    K.set_session(get_session())

    if os.path.exists(AM_MODEL_DIR):
        print("Load acoustic model...")
        model.ctc_model.load_weights(AM_MODEL_DIR)

    ckpt = "model_{epoch:02d}-{val_loss:.2f}.hdf5"
    checkpoint = ModelCheckpoint(
        filepath=os.path.join(AM_LOG_DIR, ckpt),
        monitor="val_loss", save_weights_only=False,
        verbose=1, save_best_only=True
    )

    model_name = "acoustic_model_{}".format(MODEL_TYPE)
    tensorboard = TensorBoard(log_dir=get_board_log_path(model_name), batch_size=BATCH_SIZE)

    model.train_model.fit_generator(
        TRAIN_BATCH, epochs=N_EPOCH, verbose=1,  callbacks=[checkpoint, tensorboard], steps_per_epoch=BATCH_NUM,
        validation_data=DEV_BATCH, validation_steps=200, use_multiprocessing=True, workers=4
    )
    model.ctc_model.save(AM_MODEL_DIR)

