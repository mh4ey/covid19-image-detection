
# common imports
import os
import matplotlib.pylab as plt
from sklearn.model_selection import train_test_split

# TensorFlow ≥2.0 is required
import tensorflow as tf
from tensorflow import keras
assert tf.__version__ >= "2.0"

# To Avoid GPU errors
physical_devices = tf.config.list_physical_devices('GPU')
try:
  tf.config.experimental.set_memory_growth(physical_devices[0], True)
except:
  # Invalid device or cannot modify virtual devices once initialized.
  pass

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# TensorFlow ≥2.0 is required
import tensorflow as tf
from tensorflow import keras
assert tf.__version__ >= "2.0"


#callback setup
from tensorflow.keras.callbacks import ModelCheckpoint, LearningRateScheduler, EarlyStopping, ReduceLROnPlateau

checkpoint_path = '../models/xray_class_weights.best.hdf5'
checkpoint = ModelCheckpoint(checkpoint_path, monitor='val_loss', verbose=1, 
                             save_best_only=True, mode='min', save_weights_only = True)

early = EarlyStopping(monitor="val_loss", min_delta = 1e-4, patience = 5, mode = 'min', 
                    restore_best_weights = True, verbose = 1)

reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience = 2, verbose = 1, 
                                min_delta = 1e-4, min_lr = 1e-6, mode = 'min', cooldown=1)

callbacks = [checkpoint, early, reduce_lr]



def get_base_model(model_name :str = 'ResNet50V2', freeze_layers:bool = False, image_shape : tuple = (224,224,3)):
    """ returns pretrained model

    Args:
        model_name (str): model_name values pretrained_models = ['ResNet50V2', 'MobileNetV2', 'VGG16']
    """
    if model_name == 'ResNet50V2' :
        print(f"Downloading ResNet50V2")
        base_model = tf.keras.applications.ResNet50V2(input_shape=image_shape,
                                               include_top=False,
                                               weights='imagenet')
    elif model_name == 'MobileNetV2' :
        print(f"Downloading MobileNetV2")
        base_model = tf.keras.applications.MobileNetV2(input_shape=image_shape,
                                               include_top=False,
                                               weights='imagenet')
    elif model_name == 'VGG16' :
        print(f"Downloading VGG16")
        base_model = tf.keras.applications.VGG16(input_shape=image_shape,
                                               include_top=False,
                                               weights='imagenet')
    if freeze_layers == True:
        for layer in base_model.layers:
            layer.trainable = False
            #assert layer.trainable is False
    
    return base_model


def compile_binary_classifier(model, learning_rate, optimizer = 'Adam'):
    """[summary]

    Args:
        model ([tensorflow.keras.Model]): classifier model
        learning_rate ([float]): [description]
        optimizer ([tensorflow.keras.optimizers]): optimizer
    """
    if optimizer == 'Adam':
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=learning_rate,
            beta_1=0.9,
            beta_2=0.999,
            epsilon=1e-07,
            amsgrad=True,
            name="Adam"
            )

    
    model.compile(optimizer = optimizer,
                  #loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  #loss =tf.keras.losses.CategoricalCrossentropy(),
                  #loss=get_weighted_loss(pos_weights, neg_weights),
                  #metrics=['accuracy']
                  loss = tf.keras.losses.binary_crossentropy,
                  #metrics =['binary_accuracy', 'mae', 'auc']
                  metrics = [keras.metrics.MAE, 
                             keras.metrics.AUC(name='auc',multi_label=True),
                             keras.metrics.BinaryAccuracy(threshold=0.65),
                             keras.metrics.FalseNegatives(),
                             keras.metrics.FalsePositives(), 
                             ]
                  )
    
    return model

def compile_classifier(model, learning_rate, optimizer = 'Adam' , activation:str = 'softmax'):
    """[summary]

    Args:
        model ([tensorflow.keras.Model]): classifier model
        learning_rate ([float]): [description]
        optimizer ([tensorflow.keras.optimizers]): optimizer
    """
    if optimizer == 'Adam':
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=learning_rate,
            beta_1=0.9,
            beta_2=0.999,
            epsilon=1e-07,
            amsgrad=True,
            name="Adam"
            )
    if activation == 'softmax':
        model.compile(optimizer = optimizer,
            loss =tf.keras.losses.CategoricalCrossentropy(),
            metrics=['accuracy'])
    elif activation == 'sigmoid':
        model.compile(optimizer = optimizer,
            loss = tf.keras.losses.binary_crossentropy,
            metrics = [keras.metrics.MAE, 
                             keras.metrics.AUC(name='auc',multi_label=True),
                             keras.metrics.BinaryAccuracy(threshold=0.65),
                             keras.metrics.FalseNegatives(),
                             keras.metrics.FalsePositives(), 
                             ]
                  )
    
    return model

def get_base_model_with_new_toplayer(base_model, 
                                     freeze_layers: bool = False, 
                                     num_classes: int = 15,
                                     activation: str = 'softmax',  # softmax or sigmoid
                                     learning_rate: float = 0.01,
                                     input_shape : tuple = (224,224,3)):
    """ add a classifier

    Args:
        base_model ([keras.Model]): base_model
        num_classes ([int]) : number classes
    """
    base_model = get_base_model(base_model,freeze_layers,input_shape)
    head_model = base_model.output
    head_model = keras.layers.Flatten(name="flatten")(head_model)
    head_model = keras.layers.Dense(num_classes,activation=activation)(head_model)
    model = keras.Model(inputs=base_model.input, outputs=head_model)
    model = compile_classifier(model, learning_rate, activation)
    return model



def fine_tune_model(model, learning_rate =0.00001, optimizer = 'Adam',  fine_tune_at_layer:int=178):
    # Freeze all the layers before the `fine_tune_at` layer
    for layer in model.layers[fine_tune_at_layer:]:
        layer.trainable =  True
    compile_classifier(model, learning_rate = learning_rate, optimizer=optimizer)
    return model




def fit_model(model,train_ds,
    validation_ds, 
    num_epochs: int = 20, batch_size: int = 32):
    history = model.fit(train_ds,
                    epochs=num_epochs,
                    validation_data=validation_ds,
                    steps_per_epoch = len(train_ds)//batch_size,#steps_per_epoch = 100, 
                    validation_steps=len(validation_ds)//batch_size, #validation_steps= 25, 
                    callbacks=callbacks)
    return history

def plot_epocs_vs_val_loss(history):
    plt.figure(figsize = (12, 6))
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.plot( history.history["loss"], label = "Training Loss", marker='o')
    plt.plot( history.history["val_loss"], label = "Validation Loss", marker='+')
    plt.grid(True)
    plt.legend()
    plt.show()

def plot_epocs_vs_auc(history):
    plt.figure(figsize = (12, 6))
    plt.xlabel("Epochs")
    plt.ylabel("AUC")
    plt.plot( history.history["auc"], label = "Training AUC" , marker='o')
    plt.plot( history.history["val_auc"], label = "Validation AUC", marker='+')
    plt.grid(True)
    plt.legend()
    plt.show()


