from .rel_toolbox_lite import count_vocab_size, modality_weight_rel2abs
import artm

# change log style
lc = artm.messages.ConfigureLoggingArgs()
lc.minloglevel = 3
lib = artm.wrapper.LibArtm(logging_config=lc)


def add_standard_scores(
        model,
        dictionary,
        main_modality="@lemmatized",
        all_modalities=("@lemmatized", "@ngramms")
):
    """
    Adds standard scores for the model.

    """
    assert main_modality in all_modalities, "main_modality must be part of all_modalities"

    model.scores.add(artm.scores.PerplexityScore(
        name='PerplexityScore@all',
        class_ids=all_modalities
    ))

    model.scores.add(
        artm.scores.SparsityThetaScore(name='SparsityThetaScore')
    )

    for modality in all_modalities:
        model.scores.add(artm.scores.SparsityPhiScore(
            name=f'SparsityPhiScore{modality}', class_id=modality)
        )
        model.scores.add(artm.scores.PerplexityScore(
            name=f'PerplexityScore{modality}',
            class_ids=[modality]
        ))
        model.scores.add(
            artm.TopicKernelScore(name=f'TopicKernel{modality}',
                                  probability_mass_threshold=0.3, class_id=modality)
        )


def init_model(topic_names, seed=None, class_ids=None):
    """
    Creates basic artm model

    """
    model = artm.ARTM(
        topic_names=topic_names,
        num_processors=3,
        theta_columns_naming='title',
        show_progress_bars=False,
        class_ids=class_ids,
        seed=seed
    )

    return model


def init_simple_default_model(
        dataset, modalities_to_use, main_modality,
        specific_topics, background_topics,
):
    """
    Creates simple artm model with standard scores.

    Parameters
    ----------
    dataset : Dataset
    modalities_to_use : list of str
    main_modality : str
    specific_topics : list or int
    background_topics : list or int

    Returns
    -------
    model: artm.ARTM() instance
    """
    if isinstance(specific_topics, list):
        specific_topic_names = list(specific_topics)
    else:
        specific_topics = int(specific_topics)
        specific_topic_names = [
            f'topic_{i}'
            for i in range(specific_topics)
        ]
    n_specific_topics = len(specific_topic_names)
    if isinstance(background_topics, list):
        background_topic_names = list(background_topics)
    else:
        background_topics = int(background_topics)
        background_topic_names = [
            f'background_{n_specific_topics + i}'
            for i in range(background_topics)
        ]
    n_background_topics = len(background_topic_names)
    dictionary = dataset.get_dictionary()

    baseline_class_ids = {class_id: 1 for class_id in modalities_to_use}
    tokens_data = count_vocab_size(dictionary, modalities_to_use)
    abs_weights = modality_weight_rel2abs(tokens_data, baseline_class_ids, main_modality)

    model = init_model(
        topic_names=specific_topic_names + background_topic_names,
        class_ids=abs_weights,
    )

    if n_background_topics > 0:
        model.regularizers.add(
            artm.SmoothSparsePhiRegularizer(
                 name='smooth_phi_bcg',
                 topic_names=background_topic_names,
                 tau=0.0,
                 class_ids=[main_modality],
            ),
        )
        model.regularizers.add(
            artm.SmoothSparseThetaRegularizer(
                 name='smooth_theta_bcg',
                 topic_names=background_topic_names,
                 tau=0.0,
            ),
        )

    model.initialize(dictionary)
    add_standard_scores(model, dictionary, main_modality=main_modality,
                        all_modalities=modalities_to_use)

    return model
