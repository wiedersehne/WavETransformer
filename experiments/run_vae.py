import torch
from source.vae import create_vanilla_vae
# Decoder
from source.models.linear_decoder import WrappedLinearDecoder
from source.models.coefficient_decoder import CoefficientDecoder
from source.models.sequence_encoder import SequenceEncoder

# Set device
torch.cuda.empty_cache()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# def test(trained_model, data_module):
#
#     if False:
#         # TODO: replace with plotting
#         predictions, labels = [], []
#         for idx_batch, batch in enumerate(data_module.test_dataloader()):
#             x_test = batch['feature'].to(device)
#             _, output = trained_model(x_test)
#             prediction = torch.argmax(output, dim=1).tolist()
#
#             label = batch['label'].tolist()
#             for i in range(len(label)):
#                 predictions.append(prediction[i])
#                 labels.append((label[i]))
#
#         print(data_module.label_encoder.classes_)
#         print(type(data_module.label_encoder.classes_[0]))
#
#         cm = confusion_matrix(labels, predictions)
#         df_cm = pd.DataFrame(
#             cm, index=data_module.label_encoder.classes_, columns=data_module.label_encoder.classes_
#         )
#         show_confusion_matrix(df_cm)
#
#
# def visualise_latent(model, data_module):
#
#     batch_train = next(iter(data_module.train_dataloader()))
#     batch_test = next(iter(data_module.test_dataloader()))
#     batch_val = next(iter(data_module.val_dataloader()))
#
#     sequences = torch.cat((batch_train['feature'],
#                            batch_test['feature'],
#                            batch_val['feature']
#                            ), 0)
#     labels = torch.cat((batch_train['label'],
#                         batch_test['label'],
#                         batch_val['label']
#                         ), 0)
#     #print(sequences.shape)
#
#     model = copy.deepcopy(model)
#     model.write_embeddings(x=sequences.to(device), y=labels)
#     model.create_tensorboard_log(metadata=labels.detach().cpu().numpy())


def simulated_dm():
    from data.simulatedMarkov.loader import MarkovDataModule as DataModule
    return DataModule(classes=3, steps=2, n=10000, length=20, n_class_bases=2, n_bases_shared=0)


def ascat_dm():
    from data.ASCAT.loader import ASCATDataModule as DataModule
    cancer_types = ['OV', 'STAD']   # ['STAD', 'COAD']
    return DataModule(cancer_types=cancer_types, batch_size=32)


def main(simulated=False):

    # Load data and filter for only the cases of interest
    if simulated:
        import numpy as np
        dm = simulated_dm()
        chrom_channels, out_channels = 1, 1
        stacked_bases = np.vstack(dm.bases)
        seq_length = 20
        latent_dimension = stacked_bases.shape[0]
    else:
        dm = ascat_dm()
        chrom_channels, out_channels = 23, 23
        seq_length = 1000
        latent_dimension = 40

    print(dm)

    # Create encoder
    encoder = SequenceEncoder(out_dim=latent_dimension, n_hidden=64, n_layers=3, dropout=0.,
                              bidirectional=True, stack=1, in_channels=chrom_channels, out_channels=out_channels,
                              kernel_size=3, stride=5, padding=1)

    # Create decoder
    # decoder = CoefficientDecoders(in_features=latent_dimension, bases=stacked_bases)
    decoder = WrappedLinearDecoder(in_features=latent_dimension,
                                   length=seq_length, chromosomes=chrom_channels, strands=2,
                                   hidden_features=32)

    # Validation set
    val_iterator = iter(dm.val_dataloader())
    # batches = 3
    # for i in range(batches):
    #     feature, label = next(val_iterator)

    # Create model
    model, trainer = create_vanilla_vae(encoder_model=encoder, decoder_model=decoder,
                                        latent_dim=latent_dimension, kld_weight=2,
                                        validation_hook_batch=next(val_iterator),
                                        )

    # Train model
    trainer.fit(model, datamodule=dm)
    trained_model = model.load_checkpoint(trainer.checkpoint_callback.best_model_path)
    trained_model.freeze()

    # Test model
    trainer.test(trained_model, dataloaders=dm.test_dataloader())


if __name__ == '__main__':

    main(simulated=False)
