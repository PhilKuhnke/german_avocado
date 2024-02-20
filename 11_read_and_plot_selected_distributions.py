import itertools
import matplotlib
import mne
import numpy
import os
import random
import scipy

from matplotlib import pyplot
from scipy import stats

### reading ratings
full_words = list()
with open(os.path.join('output', 'candidate_nouns_all_variables.tsv')) as i:
    for l_i, l in enumerate(i):
        line = l.strip().split('\t')
        if l_i == 0:
            header = line.copy()
            variables = {h : dict() for h in line[1:] if 'lemma' not in h and h not in ['predicted_dominance', 'predicted_arousal', 'predicted_valence']}
        else:
            for h, val in zip(header, line):
                if h == 'word':
                    word = val
                    full_words.append(word)
                elif 'lemma' in h:
                    continue
                elif h in ['predicted_dominance', 'predicted_arousal', 'predicted_valence']:
                    continue
                else:
                    if val.isnumeric():
                        val = float(val)
                        if 'gram' in h:
                            val = numpy.log10(val)
                    variables[h][word] = val

remove = [
          'predicted_leg', 
          'predicted_haptic', 
          'predicted_mouth', 
          'predicted_head', 
          'predicted_torso', 
          #'predicted_visual',
          #'predicted_olfactory',
          #'predicted_gustatory',
          #'predicted_hearing',
          ]
relevant_keys = [h for h in variables.keys() if 'en_' not in h and 'raw_' not in h and h not in remove and 'proto' not in h]

amount_stim = 36

### reading words from previous experiments
old_file = os.path.join('output', 'phil_original_annotated_clean.tsv')
old_goods = dict()
localizer = dict()
with open(old_file) as i:
    for l_i, l in enumerate(i):
        line = l.strip().split('\t')
        if l_i == 0:
            included = line.index('Included')
            action = line.index('Action')
            sound = line.index('Sound')
            word = line.index('Words')
            continue
        eval_val = float(line[included].replace(',', '.'))
        #print(eval_val)
        assert eval_val >= 0. and eval_val <=1.
        if eval_val == 0.:
            continue
        curr_action = float(line[action].replace(',', '.'))
        curr_sound = float(line[sound].replace(',', '.'))
        assert curr_action in [0., 1.] and curr_sound in [0., 1.]
        if curr_action > 0. and curr_sound > 0.:
            label = 'highA_highS'
        if curr_action == 0. and curr_sound == 0.:
            label = 'lowA_lowS'
        if curr_action == 0. and curr_sound > 0.:
            label = 'lowA_highS'
        if curr_action > 0. and curr_sound == 0.:
            label = 'highA_lowS'
        if label not in old_goods.keys():
            old_goods[label] = set()
            localizer[label] = set()
        if line[word] not in full_words:
            print(line[word])
            continue
        if eval_val < 0.9:
            if eval_val > 0.5:
                localizer[label].add(line[word])
        else:
            old_goods[label].add(line[word])
print('old items')
print([(k, len(v)) for k, v in old_goods.items()])
print('old localizers')
print([(k, len(v)) for k, v in localizer.items()])

### testing p-vals
ps = list()
cases = list()

for mode in (
             'original_exp',
             'good_only', 
             #'good_mid',
             ):
    print('{}\n\n'.format(mode))

    ### reading selected nouns
    good = {l : v for l, v in old_goods.items()}
    if mode != 'original_exp':


        folder = 'Stimuli_annotated'
        for f in os.listdir(folder):
            if 'tsv' not in f:
                continue
            ### category
            label = '_'.join(f.split('_')[:2])
            #if label not in good.keys():
            #    good[label] = set()
            with open(os.path.join(folder, f)) as i:
                for l_i, l in enumerate(i):
                    if l_i == 0:
                        continue
                    line = l.strip().split('\t')
                    if line[0] == 'word':
                        continue
                    if mode == 'good_only':
                        if line[1] in ['mid', 'bad']:
                            continue
                        elif line[1] in ['action', 'sound']:
                            localizer[label].add(line[0])
                        else:
                            good[label].add(line[0])
                    else:
                        if line[1] in ['bad']:
                            continue
                        elif line[1] in ['action', 'sound']:
                            localizer[label].add(line[0])
                        else:
                            good[label].add(line[0])
        print('localizer items')
        print([(k, len(v)) for k, v in localizer.items()])
    ### plotting distributions
    print('good items')
    print([(k, len(v)) for k, v in good.items()])
    print('localizer items')
    print([(k, len(v)) for k, v in localizer.items()])

    ### plotting violinplots
    violin_folder = os.path.join('violins', mode)
    os.makedirs(violin_folder, exist_ok=True)
    xs = [val for val in good.keys()]
    for k in relevant_keys:
        #print(k)
        xs = [val for val in good.keys()]
        combs = list(itertools.combinations(xs, r=2))
        vals = {xs[_] : [float(variables[k][w]) for w in good[xs[_]]] for _ in range(len(xs))}
        for c in combs:
            p = scipy.stats.ttest_ind(vals[c[0]], vals[c[1]]).pvalue
            ps.append(p)
            cases.append([k, c[0], c[1]])
        file_name = os.path.join(violin_folder, '{}.jpg'.format(k))
        fig, ax = pyplot.subplots(constrained_layout=True)
        for _ in range(len(xs)):
            ax.violinplot(positions=[_], dataset=[float(variables[k][w]) for w in good[xs[_]]], showmeans=True)
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([x.replace('_', '_') for x in xs])
        ax.set_title('{} distributions for selected words'.format(k))
        pyplot.savefig(file_name)
        pyplot.clf()
        pyplot.close()
    corrected_ps = mne.stats.fdr_correction(ps)[1]
    #for case, p in zip(cases, corrected_ps):
    for case, p in zip(cases, ps):
        if p<=0.05:
            print([case, p])
#print(k)

### propose selection of stimuli
'''
### compute averages for each condition

idxs = [var for var in relevant_keys if 'hand' not in var and 'auditory' not in var]
exp_idxs = [var for var in relevant_keys if 'hand' in var or 'auditory' in var]
distances = {w : list() for v in good.values() for w in v}
### criterion: average across all
variable_avgs = {var: numpy.average([float(variables[var][w]) for k, v in good.items() for w in v]) for var in idxs}
exp_avgs = {var: numpy.average([float(variables[var][w]) for k, v in good.items() for w in v]) for var in exp_idxs}
for _, v in good.items():
    for w in v:
        for var, var_avg in variable_avgs.items():
            distances[w].append(abs(float(variables[var][w])-var_avg))

        if 'lowS' in _:
            distances[w].append(abs(exp_avgs['predicted_auditory']-float(variables['predicted_auditory'][w])))
        elif 'highS' in _:
            distances[w].append(abs(float(variables['predicted_auditory'][w])-exp_avgs['predicted_auditory']))
        if 'lowA' in _:
            distances[w].append(abs(exp_avgs['predicted_hand']-float(variables['predicted_hand'][w])))
        elif 'highA' in _:
            distances[w].append(abs(float(variables['predicted_hand'][w])-exp_avgs['predicted_hand']))
distances = {k : numpy.average(v) for k, v in distances.items()}
'''

distances = dict()
for good_k, v in good.items():
    split_k = good_k.split('_')
    ### every word
    for w in v:
        distances[w] = list()
        ### the thing we really care about are hand and audition
        for var_i, var in enumerate([
                                     'predicted_hand', 
                                     'predicted_auditory',
                                     ]):
            ### promoting similarity
            rel_keys = [k for k in good.keys() if split_k[var_i] in k and k!=good_k]
            #assert len(rel_keys) == 2
            assert len(rel_keys) == 1
            rel_vals = [float(variables[var][w_two]) for key in rel_keys for w_two in good[key]]
            rel_avg = numpy.average(rel_vals)
            dist = abs(rel_avg-float(variables[var][w]))
            distances[w].append(dist)
            ### promoting dissimilarity
            unrel_keys = [k for k in good.keys() if split_k[var_i] not in k]
            assert len(unrel_keys) == 2
            rel_vals = [float(variables[var][w_two]) for key in unrel_keys for  w_two in good[key]]
            rel_avg = numpy.average(rel_vals)
            dist = -abs(rel_avg-float(variables[var][w]))
            distances[w].append(dist)
            ### also trying to match more fundamental variables
            for rel, more_var in enumerate([
                             'log10_word_frequency_sdewac',
                             'old20_score',
                             #'word_average_bigram_frequency',
                             #'word_average_trigram_frequency',
                             ]):
                rel_vals = [float(variables[more_var][w_two]) for key in rel_keys for w_two in good[key]]
                rel_avg = numpy.average(rel_vals)
                dist = (0.5/(rel+1))*abs(rel_avg-float(variables[more_var][w]))
                distances[w].append(dist)
distances = {w : numpy.average(v) for w, v in distances.items()}

best_good = {label : {w : distances[w] for w in v} for label, v in good.items()}
best_good = {label : [w[0] for w in sorted(v.items(), key=lambda item : item[1])] for label, v in best_good.items()}
selected_words = {k : v[:amount_stim*2] for k, v in best_good.items()}
### criterion: average separately for high/low action/sound
#best_good = {k : random.sample(list(v), k=len(v)) for k, v in good.items()}
for v in selected_words.values():
    assert len(v) == amount_stim*2

### plotting violinplots
violin_folder = os.path.join('violins', 'best_for_experiment')
os.makedirs(violin_folder, exist_ok=True)
xs = [val for val in best_good.keys()]
### testing p-vals
ps = list()
cases = list()
combs = list(itertools.combinations(xs, r=2))
for k in relevant_keys:
    vals = {xs[_] : [float(variables[k][w]) for w in selected_words[xs[_]]] for _ in range(len(xs))}
    for c in combs:
        p = scipy.stats.ttest_ind(vals[c[0]], vals[c[1]]).pvalue
        ps.append(p)
        cases.append([k, c[0], c[1]])
    file_name = os.path.join(violin_folder, '{}.jpg'.format(k))
    fig, ax = pyplot.subplots(constrained_layout=True)
    for _ in range(len(xs)):
        ax.violinplot(positions=[_], dataset=[float(variables[k][w]) for w in best_good[xs[_]][:amount_stim*2]], showmeans=True)
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels([x.replace('_', '_') for x in xs])
    ax.set_title('{} distributions for selected words'.format(k))
    pyplot.savefig(file_name)
    pyplot.clf()
    pyplot.close()

corrected_ps = mne.stats.fdr_correction(ps)[1]
#for case, p in zip(cases, ps):
for case, p in zip(cases, corrected_ps):
    if p<=0.05:
        print([case, p])
print(k)

### writing to files the pairwise tests
with open('pairwise_comparisons_main_experiment.tsv', 'w') as o:
    o.write('variable\tlow_sound_avg_zscore\thigh_sound_std\tsound_T\tsound_p\t'\
                      'low_action_avg_zscore\thigh_action_std\taction_T\taction_p\n')
    for k in relevant_keys:
        o.write('{}\t'.format(k))
        ### sound
        low_sound = [float(variables[k][w])  for _ in xs for w in selected_words[_] if 'lowS' in _]
        o.write('{}\t{}\t'.format(round(numpy.average(low_sound), 4),round(numpy.std(low_sound), 4)))
        hi_sound = [float(variables[k][w]) for _ in xs for w in selected_words[_] if 'highS' in _]
        o.write('{}\t{}\t'.format(round(numpy.average(hi_sound), 4),round(numpy.std(hi_sound), 4)))
        stat_comp = scipy.stats.ttest_ind(low_sound, hi_sound)
        o.write('{}\t{}\t'.format(round(stat_comp.statistic, 4),round(stat_comp.pvalue, 5)))
        ### action
        low_action = [float(variables[k][w]) for _ in xs for w in selected_words[_] if 'lowA' in _]
        o.write('{}\t{}\t'.format(round(numpy.average(low_action), 4),round(numpy.std(low_action), 4)))
        hi_action = [float(variables[k][w]) for _ in xs for w in selected_words[_] if 'highA' in _]
        o.write('{}\t{}\t'.format(round(numpy.average(hi_action), 4),round(numpy.std(hi_action), 4)))
        stat_comp = scipy.stats.ttest_ind(low_action, hi_action)
        o.write('{}\t{}\n'.format(round(stat_comp.statistic, 4),round(stat_comp.pvalue, 5)))

with open('main_experiment_words.tsv', 'w') as o:
    o.write('word\tcategory\n')
    for cat, ws in selected_words.items():
        for w in ws:
            o.write('{}\t{}\n'.format(w, cat))

'''
### localizer now
xs = [val for val in best_good.keys()]
passage_localizer = {_ : set(best_good[_][amount_stim*2:]) | localizer[_] for _ in xs}
all_localizer = {

distances = dict()
for k, v in all_localizer.items():
    split_k = k.split('_')
    ### every word
    for w in v:
        distances[w] = list()
        ### the thing we really care about are hand and audition
        for var_i, var in enumerate(['predicted_hand', 'predicted_auditory']):
            rel_keys = [k for k in all_localizer.keys() if split_k[var_i] in k]
            rel_vals = [float(variables[var][w_two]) for key in rel_keys for  w_two in all_localizer[key]]
            dist = abs(numpy.average(rel_vals)-float(variables[var][w]))
            distances[w].append(dist)
distances = {w : numpy.average(v) for w, v in distances.items()}

best_localizer = {label : {w : distances[w] for w in v} for label, v in all_localizer.items()}
best_localizer = {label : [w[0] for w in sorted(v.items(), key=lambda item : item[1])][:int(amount_stim*0.5)] for label, v in best_localizer.items()}
### criterion: average separately for high/low action/sound
#best_good = {k : random.sample(list(v), k=len(v)) for k, v in good.items()}
for v in best_localizer.values():
    assert len(v) == int(amount_stim*0.5)

### plotting violinplots
violin_folder = os.path.join('violins', 'best_for_localizer')
os.makedirs(violin_folder, exist_ok=True)
for k in relevant_keys:
    print(k)
    file_name = os.path.join(violin_folder, '{}.jpg'.format(k))
    fig, ax = pyplot.subplots(constrained_layout=True)
    for _ in range(len(xs)):
        ax.violinplot(positions=[_], dataset=[float(variables[k][w]) for w in best_localizer[xs[_]]], showmeans=True)
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels([x.replace('_', '_') for x in xs])
    ax.set_title('{} distributions for selected words'.format(k))
    pyplot.savefig(file_name)
    pyplot.clf()
    pyplot.close()

### writing to files the pairwise tests
with open('pairwise_comparisons_localizer.tsv', 'w') as o:
    o.write('variable\tlow_sound_avg_zscore\thigh_sound_std\tsound_T\tsound_p\t'\
                      'low_action_avg_zscore\thigh_action_std\taction_T\taction_p\n')
    for k in relevant_keys:
        o.write('{}\t'.format(k))
        ### sound
        low_sound = [[float(variables[k][w]) for w in best_localizer[_] for _ in xs if 'lowS' in _]
        o.write('{}\t{}\t'.format(round(numpy.average(low_sound), 4),round(numpy.std(low_sound), 4)))
        hi_sound = [[float(variables[k][w]) for w in best_localizer[_] for _ in xs if 'highS' in _]
        o.write('{}\t{}\t'.format(round(numpy.average(hi_sound), 4),round(numpy.std(hi_sound), 4)))
        stat_comp = scipy.stats.ttest_ind(low_sound, hi_sound)
        o.write('{}\t{}\t'.format(round(stat_comp.statistic, 4),round(stat_comp.pvalue, 5)))
        ### action
        low_action = [[float(variables[k][w]) for w in best_localizer[_] for _ in xs if 'lowA' in _]
        o.write('{}\t{}\t'.format(round(numpy.average(low_action), 4),round(numpy.std(low_action), 4)))
        hi_action = [[float(variables[k][w]) for w in best_localizer[_] for _ in xs if 'highA' in _]
        o.write('{}\t{}\t'.format(round(numpy.average(hi_action), 4),round(numpy.std(hi_action), 4)))
        stat_comp = scipy.stats.ttest_ind(low_action, hi_action)
        o.write('{}\t{}\n'.format(round(stat_comp.statistic, 4),round(stat_comp.pvalue, 5)))

with open('main_experiment_words.tsv', 'w') as o:
    o.write('word\tcategory\n')
    for cat, ws in selected_words.items():
        for w in ws:
            o.write('{}\t{}\n'.format(w, cat))
'''
