import numpy as np
from malenov.segy import segy_decomp


def master(segy_filename,inp_format,cube_incr,train_dict={},pred_dict={},mode = 'full'):
    # segy_filename: filename of the segy-cube to be imported (necessary for copying the segy-frame before writing a new segy)
    # inp_format: input resolution, the formatting of the seismic cube (could be changed to 8-bit data)
    # cube_incr: number of increments included in each direction from the example to make a mini-cube
    # train_dict: Training parameters packaged as a Python dictionary
    # pred_dict: Prediciton parameters packaged as a Python dictionary
    # mode: Do we want to train a model('train'), predict using an external model('predict'), or train a model and predict using it('full')

    # Implement more than one segy-cube if the input segy_filename is a list
    if type(segy_filename) is str or (type(segy_filename) is list and len(segy_filename) == 1):
        # Check if the filename needs to be retrieved from a list
        if type(segy_filename) is list:
            segy_filename = segy_filename[0]

        # Make a master segy object
        segy_obj = segy_decomp(segy_file = segy_filename,
                               plot_data = False,
                               read_direc = 'full',
                               inp_res = inp_format)

        # Define how many segy-cubes we're dealing with
        segy_obj.cube_num = 1
        segy_obj.data = np.expand_dims(segy_obj.data, axis = 4)

    elif type(segy_filename) is list:
        # start an iterator
        i = 0

        # iterate through the list of cube names and store them in a masterobject
        for filename in segy_filename:
            # Make a master segy object
            if i == 0:
                segy_obj = segy_decomp(segy_file = filename,
                                       plot_data = False,
                                       read_direc = 'full',
                                       inp_res = inp_format)

                # Define how many segy-cubes we're dealing with
                segy_obj.cube_num = len(segy_filename)

                # Reshape and preallocate the numpy-array for the rest of the cubes
                print('Starting restructuring to 4D arrays')
                ovr_data = np.empty((list(segy_obj.data.shape) + [len(segy_filename)]))
                ovr_data[:,:,:,i] = segy_obj.data
                segy_obj.data = ovr_data
                ovr_data = None
                print('Finished restructuring to 4D arrays')
            else:
                # Add another cube to the numpy-array
                segy_obj.data[:,:,:,i] = segy_adder(segy_file = filename,
                                                    inp_cube = segy_obj.data,
                                                    read_direc = 'full',
                                                    inp_res = inp_format)
            # Increase the itterator
            i+=1
    else:
        print('The input filename needs to be a string, or a list of strings')


    print('Finished unpaking and restructuring the numpy array')


    # Are we going to perform training?
    if mode == 'train' or mode == 'full':
        # Unpack the dictionary of training parameters
        label_list = train_dict['files']
        num_bunch = train_dict['num_tot_iterations']
        num_epochs = train_dict['epochs']
        num_examples = train_dict['num_train_ex']
        batch_size = train_dict['batch_size']
        opt_patience = train_dict['opt_patience']
        data_augmentation = train_dict['data_augmentation']
        write_out = train_dict['save_model']
        write_location = train_dict['save_location']

        # If there is a model given in the prediction dictionary continue training on this model
        if 'keras_model' in pred_dict:
            keras_model = pred_dict['keras_model']
        else:
            keras_model = None

        # Print out an initial statement to confirm the parameters(QC)
        print('num full iterations:', num_bunch)
        print('num epochs:',num_epochs)
        print('num examples per epoch:',num_examples)
        print('batch size:',batch_size)
        print('optimizer patience:',opt_patience)


        # Make the list of class data
        print('Making class-adresses')
        class_array = convert(file_list = label_list,
                              save = False,
                              savename = None,
                              ex_adjust = True)

        print('Finished making class-adresses')

        # Time the training process
        start_train_time = time.time()

        # Train a new model/further train the uploaded model and store the result as the model output
        model = train_model(segy_obj = segy_obj,
                            class_array = class_array,
                            num_classes = len(label_list),
                            cube_incr = cube_incr,
                            inp_res = inp_format,
                            num_bunch = num_bunch,
                            num_epochs = num_epochs,
                            num_examples = num_examples,
                            batch_size = batch_size,
                            opt_patience = opt_patience,
                            data_augmentation = data_augmentation,
                            num_channels = segy_obj.cube_num,
                            keras_model = keras_model,
                            write_out = write_out,
                            write_location = write_location)

        # Time the training process
        end_train_time = time.time()
        train_time = end_train_time-start_train_time # seconds

        # print to the user the total time spent training
        if train_time <= 300:
            print('Total time elapsed during training:',train_time, ' sec.')
        elif 300 < train_time <= 60*60:
            minutes = train_time//60
            seconds = (train_time%60)*(60/100)
            print('Total time elapsed during training:',minutes,' min., ',seconds,' sec.')
        elif 60*60 < train_time <= 60*60*24:
            hours = train_time//(60*60)
            minutes = (train_time%(60*60))*(1/60)*(60/100)
            print('Total time elapsed during training:',hours,' hrs., ',minutes,' min., ')
        else:
            days = train_time//(24*60*60)
            hours = (train_time%(24*60*60))*(1/60)*((1/60))*(24/100)
            print('Total time elapsed during training:',days,' days, ',hours,' hrs., ')

    elif mode == 'predict':
        # If we aren't performing any training
        print('Using uploaded model for prediction')
    else:
        print('Invalid mode! Accepted inputs are ''train'', ''predict'', or ''full''')
        return None

    # Are we going to perform prediction?
    if mode == 'predict' or mode == 'full':
        # Let the user know if we have made new computations on the model used for prediction
        if mode == 'full':
            print('Using the newly computed model for prediction')
        else:
            model  = pred_dict['keras_model']

        # Unpack the prediction dictionary
        section_edge  = pred_dict['section_edge']
        xline_ref = pred_dict['xline']
        num_classes = pred_dict['num_class']
        sect_form = pred_dict['cord_syst']
        show_feature  = pred_dict['show_feature']
        save_pred = pred_dict['save_pred']
        save_loc = pred_dict['save_location']
        pred_batch = pred_dict['pred_batch']
        prob = pred_dict['pred_prob']

        # Time the prediction process
        start_pred_time = time.time()

        # Make a prediction on the master segy object using the desired model, and plot the results
        pred = visualization(filename = segy_filename,
                             inp_seis = segy_obj.data,
                             seis_obj = segy_obj,
                             keras_model = model,
                             cube_incr = cube_incr,
                             section_edge = section_edge,
                             xline_ref = xline_ref,
                             num_classes = num_classes,
                             inp_res = inp_format,
                             sect_form = sect_form,
                             save_pred = save_pred,
                             save_file = save_loc,
                             pred_batch = pred_batch,
                             show_feature = show_feature,
                             show_prob = prob)

        # Print the time taken for the prediction
        end_pred_time = time.time()
        pred_time = end_pred_time-start_pred_time # seconds

        # print to the user the total time spent training
        if pred_time <= 300:
            print('Total time elapsed during prediction:',pred_time, ' sec.')
        elif 300 < pred_time <= 60*60:
            minutes = pred_time//60
            seconds = (pred_time%60)*(60/100)
            print('Total time elapsed during prediction:',minutes,' min., ',seconds,' sec.')
        elif 60*60 < pred_time <= 60*60*24:
            hours = pred_time//(60*60)
            minutes = (pred_time%(60*60))*(1/60)*(60/100)
            print('Total time elapsed during prediction:',hours,' hrs., ',minutes,' min., ')
        else:
            days = pred_time//(24*60*60)
            hours = (pred_time%(24*60*60))*(1/60)*((1/60))*(24/100)
            print('Total time elapsed during prediction:',days,' days, ',hours,' hrs., ')

    else:
        # Make an empty variable for the prediction output
        pred = None

    # Return the new model and/or prediction as an output dictionary
    output = {
        'model' : model,
        'pred' : pred
    }

    return output