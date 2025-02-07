import numpy as np
import tensorflow as tf
import farm.adaptations.rl.tf_wrappers as tf_wrappers


class PPONetwork(tf.keras.Model):
    """Network for the PPO algorithm. Defined as a Keras Model to use the Keras training API automatically."""

    def __init__(self, inputs_count, actions_count, *,
                 common_layer_widths=[], policy_layer_widths=[100, 100], value_layer_widths=[100, 100],
                 learning_rate=0.001, entropy_regularization=0.1, clip_epsilon=0.2) -> None:

        self.entropy_regularization = entropy_regularization
        self.clip_epsilon = clip_epsilon

        input_layer = tf.keras.layers.Input((inputs_count,))

        hidden = input_layer
        for width in common_layer_widths:
            hidden = tf.keras.layers.Dense(width, activation=tf.nn.relu)(hidden)

        # policy head (discrete actions)
        policy_hidden = hidden
        for width in policy_layer_widths:
            policy_hidden = tf.keras.layers.Dense(width, activation=tf.nn.relu)(policy_hidden)
        policy = tf.keras.layers.Dense(actions_count, activation=tf.nn.softmax)(policy_hidden)

        # value head (a scalar, not a vector of length one, to avoid broadcasting errors)
        value_hidden = hidden
        for width in value_layer_widths:
            value_hidden = tf.keras.layers.Dense(width, activation=tf.nn.relu)(value_hidden)
        value = tf.keras.layers.Dense(1)(value_hidden)[:, 0]

        # Construct the model
        super().__init__(inputs=input_layer, outputs=[policy, value])

        # Compile using Adam optimizer with the given learning rate.
        self.compile(optimizer=tf.optimizers.Adam(learning_rate))

    def train_step(self, data):
        states, targets = data
        actions = targets["actions"]
        action_probs = targets["action_probs"]
        advantages = targets["advantages"]
        returns = targets["returns"]
        action_probs = tf.clip_by_value(action_probs, 1e-10, 1)  # prevent NaN (from division by almost 0)

        with tf.GradientTape() as tape:
            # Compute the policy and the value function
            policy, value = self(states, training=True)

            # PPO loss
            r = tf.gather(policy, actions, batch_dims=1) / action_probs
            r_clipped = tf.clip_by_value(r, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
            ppo_loss = -tf.reduce_mean(tf.minimum(r * advantages, r_clipped * advantages))
            # MSE error between the predicted value function and target returns
            mse_loss = tf.keras.losses.MeanSquaredError()(returns, value)
            # entropy regularization
            entropy_loss = -self.entropy_regularization * tf.keras.losses.CategoricalCrossentropy()(policy, policy)
            # total loss
            loss = ppo_loss + mse_loss + entropy_loss

        # Perform an optimizer step and return the loss for reporting and visualization.
        self.optimizer.minimize(loss, self.trainable_variables, tape=tape)
        return {"loss": loss, "ppo": ppo_loss, "mse": mse_loss, "entropy": entropy_loss}

    # Predict method, with @wrappers.raw_tf_function for efficiency.
    @tf_wrappers.typed_np_function(np.float32)
    @tf_wrappers.raw_tf_function(dynamic_dims=1)
    def predict(self, states: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return self(states)
