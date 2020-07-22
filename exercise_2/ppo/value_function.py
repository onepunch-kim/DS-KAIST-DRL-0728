"""
State-Value Function

Written by Patrick Coady (pat-coady.github.io)
"""

import tensorflow as tf
import numpy as np
from sklearn.utils import shuffle
import os

class NNValueFunction(object):
    """ NN-based state-value function """
    def __init__(self, obs_dim, hid1_mult=10):

        self.replay_buffer_x = None
        self.replay_buffer_y = None
        self.obs_dim = obs_dim
        self.hid1_mult = hid1_mult
        self.epochs = 10
        self.lr = None  # learning rate set in _build_graph()
        self.sess = tf.keras.backend.get_session()

        with tf.compat.v1.variable_scope("val_function"):
            self.obs_ph = tf.placeholder(tf.float32, (None, self.obs_dim), 'obs_valfunc')
            self.val_ph = tf.placeholder(tf.float32, (None,), 'val_valfunc')
            hid1_size = self.obs_dim * self.hid1_mult
            hid3_size = 5
            hid2_size = int(np.sqrt(hid1_size * hid3_size))
            self.lr = 1e-2 / np.sqrt(hid2_size)  # 1e-3 empirically determined

            # 3 hidden layers with tanh activations
            out = tf.keras.layers.Dense(hid1_size, tf.tanh,
                                        kernel_initializer=tf.random_normal_initializer(
                                            stddev=np.sqrt(1 / self.obs_dim)), name="h1")(self.obs_ph)
            out = tf.keras.layers.Dense(hid2_size, tf.tanh,
                                        kernel_initializer=tf.random_normal_initializer(
                                            stddev=np.sqrt(1 / hid1_size)), name="h2")(out)
            out = tf.keras.layers.Dense(hid3_size, tf.tanh,
                                        kernel_initializer=tf.random_normal_initializer(
                                            stddev=np.sqrt(1 / hid2_size)), name="h3")(out)
            out = tf.keras.layers.Dense(1,
                                        kernel_initializer=tf.random_normal_initializer(
                                            stddev=np.sqrt(1 / hid3_size)), name='output')(out)
            self.out = tf.squeeze(out)
            self.loss = tf.reduce_mean(tf.square(self.out - self.val_ph))  # squared loss
            optimizer = tf.train.AdamOptimizer(self.lr)
            self.train_op = optimizer.minimize(self.loss)

        self.sess.run(tf.global_variables_initializer())

    def fit(self, x, y, logger):

        num_batches = max(x.shape[0] // 256, 1)
        batch_size = x.shape[0] // num_batches
        y_hat = self.predict(x)  # check explained variance prior to update
        old_exp_var = 1 - np.var(y - y_hat)/np.var(y)
        if self.replay_buffer_x is None:
            x_train, y_train = x, y
        else:
            x_train = np.concatenate([x, self.replay_buffer_x])
            y_train = np.concatenate([y, self.replay_buffer_y])
        self.replay_buffer_x = x
        self.replay_buffer_y = y
        for e in range(self.epochs):
            x_train, y_train = shuffle(x_train, y_train)
            for j in range(num_batches):
                start = j * batch_size
                end = (j + 1) * batch_size
                feed_dict = {self.obs_ph: x_train[start:end, :],
                             self.val_ph: y_train[start:end]}
                _, l = self.sess.run([self.train_op, self.loss], feed_dict=feed_dict)
        y_hat = self.predict(x)
        loss = np.mean(np.square(y_hat - y))         # explained variance after update
        exp_var = 1 - np.var(y - y_hat) / np.var(y)  # diagnose over-fitting of val func

        logger.log({'ValFuncLoss': loss,
                    'ExplainedVarNew': exp_var,
                    'ExplainedVarOld': old_exp_var})
        

    def predict(self, x):
        """ Predict method """
        feed_dict = {self.obs_ph: x}
        y_hat = self.sess.run(self.out, feed_dict=feed_dict)

        return np.squeeze(y_hat)


