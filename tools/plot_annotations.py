#! /usr/bin/env python
import sys
from collections import OrderedDict
import os.path
import re

import xml.etree.ElementTree as ET

COLOR_SCHEME = {"mis":"#6bff62", 
                "ges":"#dfe934", 
                "call":"#c5008d", 
                "touch":"#32782e", 
                "rem":"#20b9ff", 
                "put":"#4852e3", 
                "exp":"#f9e0a2", 
                "talk":"#c50e00", 
                "look":"#f25329", 
                "show":"#0f5778", 
                "play":"#45170c"}

# defines which actions are used, and the *order* in which actions are stacked

ACTIONS = []

# full
ALL_ACTIONS = [ "show", "talk", "call","put", "rem", "touch", "mis", "ges", "exp", "look", "play"]

# only 'engagement'
ENGAGEMENT_ACTIONS = [ "show", "talk", "touch", "mis", "ges", "look", "play"]

rgbcolors = [COLOR_SCHEME[act]  for act in ALL_ACTIONS]
palette = "(" + ", ".join(["%s '%s'" % (i,c) for i, c in enumerate(rgbcolors)]) + ")"

def get_timeslots(xml_root):
    timeslots = {}
    times = xml_root.find("TIME_ORDER")
    for slot in times:
        timeslots[slot.attrib["TIME_SLOT_ID"]] = int(slot.attrib["TIME_VALUE"])

    return timeslots


def get_runs(xml_root, timeslots):

    runs = {}
    rawruns = xml_root.findall("./TIER[@TIER_ID='runs']")[0]

    for run in rawruns:
        run_times = run.find("ALIGNABLE_ANNOTATION").attrib
        starttime = timeslots[run_times["TIME_SLOT_REF1"]]
        endtime = timeslots[run_times["TIME_SLOT_REF2"]]
        name = run.find("ALIGNABLE_ANNOTATION").find("ANNOTATION_VALUE").text
        if name.startswith("run "):
            name = name[4:]
            runs[name] = [starttime, endtime]

    return OrderedDict(sorted(runs.items(), key=lambda t: t[0]))

def get_tiers(xml_root):
    excluded_tiers = ["runs", "scenario-time"]
    rawtiers = xml_root.findall("./TIER")
    return [a.attrib["TIER_ID"] for a in rawtiers if a.attrib["TIER_ID"] not in excluded_tiers]

def get_actions(xml_root, tier, run, timeslots):

    interactions = dict(zip(ACTIONS, [0] * len(ACTIONS)))
    rawactions = xml_root.findall("./TIER[@TIER_ID='%s']" % tier)[0]

    for action in rawactions:
        action_times = action.find("ALIGNABLE_ANNOTATION").attrib
        starttime = timeslots[action_times["TIME_SLOT_REF1"]]
        endtime = timeslots[action_times["TIME_SLOT_REF2"]]
        if starttime > run[0] and endtime < run[1]:
            name = action.find("ALIGNABLE_ANNOTATION").find("ANNOTATION_VALUE").text
            if name in interactions:
                interactions[name] += 1

    return interactions

def prepare_plot(name, interactions, samplesize, yrange = None, anthropomorphism_idx = False):
    """
    :param interactions: a dict {"run name": {"action name": occurences, "action...}, "run...}
    """
    print("Normalizing data for %s participants" % samplesize)
    for key in interactions.keys():
        interactions[key] = scale_occurences(interactions[key], 1/float(samplesize))


    with open("%s.plt"%name, "w") as f:
        f.write('set key autotitle columnheader\n')
        f.write('set xlabel "Runs"\n')
        f.write('set ylabel "Interactions per minutes/per child"\n')
        f.write("set terminal pngcairo size 800,600 enhanced font 'Verdana,10'\n")
        if yrange:
            f.write("set yrange [0:%s]\n" % yrange)
        f.write("set title '%s (n=%s)'\n" % (name, samplesize))
        f.write("set output '%s.png'\n" % name)
        f.write("set style data histograms\n")
        f.write("set style histogram rowstacked\n")
        f.write("set boxwidth 0.9 relative\n")
        f.write("set style fill solid 1.0 border -1\n")
        f.write("set palette defined %s\n" % palette)
        f.write("unset colorbox\n") # hide the palette
        f.write("plot for [i=2:%s] '%s.dat' using i:xtic(1) lt palette frac (i-2)/%s.\n" % (len(ACTIONS) + 1, name, len(ACTIONS) - 1))


    with open("%s.dat" % name, "w") as f:
        f.write("# Actions by run and type\n")
        f.write("Type\t" + "\t".join(ACTIONS) + "\n")

        for name, occurences in interactions.items():
            f.write("\"%s\"\t" % name)

            for a in ACTIONS:
                f.write("%s\t" % occurences.get(a,"-"))

            f.write("\n")


def prepare_sum_plot(name, interactions, yrange = None, anthropomorphism_idx = False):
    """
    :param interactions: a dict {"run name": {"action name": occurences, "action...}, "run...}
    """

    with open("%s.dat" % name, "w") as f:
        f.write("# Actions by subject and type\n")
        f.write("Subject\t" + "\t".join(ACTIONS) + "\n")

        for subject, occurences in interactions.items():
            f.write("\"%s\"\t" % subject)

            for a in ACTIONS:
                f.write("%s\t" % occurences.get(a,"-"))

            f.write("\n")


    with open("%s.plt"%name, "w") as f:
        f.write('set key autotitle columnheader\n')
        f.write('set xlabel "Subject"\n')
        f.write('set ylabel "Nb of Interactions"\n')
        f.write("set terminal pngcairo size 800,600 enhanced font 'Verdana,10'\n")
        if yrange:
            f.write("set yrange [0:%s]\n" % yrange)
        f.write("set title '%s'\n" % name)
        f.write("set output '%s.png'\n" % name)
        f.write("set style data histograms\n")
        f.write("set style histogram rowstacked\n")
        f.write("set boxwidth 0.9 relative\n")
        f.write("set style fill solid 1.0 border -1\n")
        f.write("set palette defined %s\n" % palette)
        f.write("unset colorbox\n") # hide the palette
        f.write("plot for [i=2:%s] '%s.dat' using i:xtic(1) lt palette frac (i-2)/%s.\n" % (len(ACTIONS) + 1, name, len(ACTIONS) - 1))


def sum_occurences(actions1, actions2):
    sum_actions = OrderedDict()
    for a in ACTIONS:
        sum_actions[a] = actions1[a] + actions2[a]

    return sum_actions

def scale_occurences(actions, scalar):
    scaled_actions = OrderedDict()
    for a in ACTIONS:
        scaled_actions[a] = float(actions[a]) * scalar

    return scaled_actions


def processfiles(name, files, perchild = False, perpair = False, yrange=None, sumplot = False):

    if sumplot and (perchild or perpair):
        timenormalization = False
    else:
        timenormalization = True
        sumplot = False

    total_interactions = 0
    interactions = OrderedDict()
    children_interactions = OrderedDict()
    groups_interactions = OrderedDict()

    for eaf in files:
        print("Processing file %s..." % eaf)
        tree = ET.parse(eaf)
        root = tree.getroot()

        timeslots = get_timeslots(root)
        runs = get_runs(root,timeslots)

        for tier in get_tiers(root):
            print("Processing subject %s..." % tier)
            for run_name, run in runs.items():
                duration = (run[1] - run[0]) / (1000. * 60) # in minutes
                print("Run %s lasted %.2fmin" % (run_name, duration))

                actions = get_actions(root, tier, run, timeslots)
                total_interactions += sum(actions.values())

                if timenormalization:
                    actions = scale_occurences(actions, 1/duration)

                if not run_name in interactions:
                    interactions[run_name] = actions 
                else:
                    interactions[run_name] = sum_occurences(interactions[run_name], actions)

            if perchild:
                print("Total interactions for %s: %s" % (tier, total_interactions))
                tiername = tier.split("_")[1]
                tiername = re.sub('\d+', lambda x:x.group().zfill(2), tiername)

                sum_interactions = interactions.values()[0]
                for run in interactions.values()[1:]:
                    sum_interactions = sum_occurences(sum_interactions, run)
                children_interactions[tiername] = sum_interactions

                if not sumplot:
                    prepare_plot(tiername, interactions, 1, yrange)

                total_interactions = 0
                interactions = OrderedDict()

        if perpair:
            print("Total interactions for this group: %s" % total_interactions)
            groupname = os.path.basename(eaf).split("_")[0]

            sum_interactions = interactions.values()[0]
            for run in interactions.values()[1:]:
                sum_interactions = sum_occurences(sum_interactions, run)
            groups_interactions[groupname] = sum_interactions

            if not sumplot:
                prepare_plot(groupname, interactions, 2, yrange)

            total_interactions = 0
            interactions = OrderedDict()


    if sumplot:
        if perchild:
            prepare_sum_plot(name, 
                            OrderedDict(sorted(children_interactions.items())),
                            yrange)
        else:
            prepare_sum_plot(name, 
                            OrderedDict(sorted(groups_interactions.items())), 
                            yrange)

    elif not perchild and not perpair:
        print("Total interactions: %s" % total_interactions)
        prepare_plot(name, interactions, len(files) * 2, yrange)


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='Generating datasets for the Domino experiment')
    parser.add_argument('-a', '--all', action='store_true',
                                help='keep all interactions (not only engagement related ones')
    parser.add_argument('-p', '--perpair', action='store_true',
                                help='generate one dataset per pair of children')
    parser.add_argument('-c', '--perchild', action='store_true',
                                help='generate one dataset per child')
    parser.add_argument('-s', '--sum', action='store_true',
                                help='shows the interaction sums per child/group')
    parser.add_argument('-y', '--yrange', default = None, type=int,
            help='Nb interactions range (default:auto)')
    parser.add_argument('name', default="default", help="base name of the plot")
    parser.add_argument('eaf', default="", nargs='+', help="Elan .eaf files to process")

    args = parser.parse_args()

    if args.all:
        ACTIONS = ALL_ACTIONS
    else:
        ACTIONS = ENGAGEMENT_ACTIONS
    processfiles(args.name, args.eaf, args.perchild, args.perpair, args.yrange, args.sum)
