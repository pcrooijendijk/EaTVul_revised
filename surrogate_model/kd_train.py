import tensorflow as tf
tf.random.set_seed(7)
from sur_model import *
from tensorflow.keras import layers
import tensorflow_datasets as tfds

tfds.disable_progress_bar()

# Average the loss across the batch size within an epoch
train_loss = tf.keras.metrics.Mean(name="train_loss")
valid_loss = tf.keras.metrics.Mean(name="test_loss")

# Specify the performance metric
train_acc = tf.keras.metrics.F1Score(name="train_acc")
valid_acc = tf.keras.metrics.F1Score(name="valid_acc")


# Define the training loop

def get_kd_loss(student_logits, teacher_logits,
                true_labels, temperature,
                alpha, beta):
    teacher_probs = tf.nn.softmax(teacher_logits / temperature)
    kd_loss = tf.keras.losses.categorical_crossentropy(
        teacher_probs, student_logits / temperature,
        from_logits=True)

    ce_loss = tf.keras.losses.sparse_categorical_crossentropy(
        true_labels, student_logits, from_logits=True)

    total_loss = (alpha * kd_loss) + (beta * ce_loss)
    return total_loss / (alpha + beta)


class Student(tf.keras.Model):
    def __init__(self, teacher_train_logits, teacher_test_logits, student,
                 temperature=5., alpha=0.9, beta=0.1):
        super(Student, self).__init__()
        self.teacher_train_logits = teacher_train_logits
        self.teacher_test_logits = teacher_test_logits
        self.student = student
        self.temperature = temperature
        self.alpha = alpha
        self.beta = beta

    def train_step(self, data):
        images, labels = data
        teacher_tr_logits = self.teacher_train_logits

        with tf.GradientTape() as tape:
            student_logits = self.student(images)
            loss = get_kd_loss(student_logits, teacher_tr_logits,
                               labels, self.temperature,
                               self.alpha, self.beta)
        gradients = tape.gradient(loss, self.student.trainable_variables)
        # As mentioned in Section 2 of https://arxiv.org/abs/1503.02531
        gradients = [gradient * (self.temperature ** 2) for gradient in gradients]
        self.optimizer.apply_gradients(zip(gradients, self.student.trainable_variables))

        train_loss.update_state(loss)
        train_acc.update_state(labels, tf.nn.softmax(student_logits))
        t_loss, t_acc = train_loss.result(), train_acc.result()
        train_loss.reset_states(), train_acc.reset_states()
        return {"train_loss": t_loss, "train_accuracy": t_acc}

    def test_step(self, data):
        images, labels = data
        teacher_logits = self.trained_teacher(images)

        student_logits = self.student(images, training=False)
        loss = get_kd_loss(student_logits, teacher_logits,
                           labels, self.temperature,
                           self.alpha, self.beta)

        valid_loss.update_state(loss)
        valid_acc.update_state(labels, tf.nn.softmax(student_logits))
        v_loss, v_acc = valid_loss.result(), valid_acc.result()
        valid_loss.reset_states(), valid_acc.reset_states()
        return {"loss": v_loss, "accuracy": v_acc}