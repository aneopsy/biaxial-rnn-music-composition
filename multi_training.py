import os, random
from midi_to_statematrix import *
from data import *
import cPickle as pickle

import signal

batch_width = 10 # number of sequences in a batch
batch_len = 16*8 # length of each sequence
division_len = 16 # interval between possible start locations

def loadPieces(dirpath):
    print("getPieceSegment")

    print("MIDI Input highest note: " + midi2note(upperBound))
    print("MIDI Input lowest  note: " + midi2note(lowerBound) + "\n")

    pieces = {}

    for fname in os.listdir(dirpath):
        printname = fname
        if fname[-4:] not in ('.mid','.MID'):
            continue

        name = fname[:-4]
        print("\n" + printname)

        outMatrix = midiToNoteStateMatrix(os.path.join(dirpath, fname))
        if len(outMatrix) < batch_len:
            continue

        pieces[name] = outMatrix
        print "Loaded {}".format(name)

    return pieces

def getPieceSegment(pieces):
    print("getPieceSegment")
    piece_output = random.choice(pieces.values())
    start = random.randrange(0, len(piece_output) - batch_len, division_len)
    print "Range is {} {} {} -> {}".format(0, len(piece_output) - batch_len, division_len, start)

    seg_out = piece_output[start:start+batch_len]
    seg_in = noteStateMatrixToInputForm(seg_out)

    return seg_in, seg_out

def getPieceBatch(pieces):
    print "getPieceBatch"
    i,o = zip(*[getPieceSegment(pieces) for _ in range(batch_width)])
    return numpy.array(i), numpy.array(o)

def trainPiece(model,pieces,epochs,start=0):
    print "trainPiece"

    stopflag = [False]
    def signal_handler(signame, sf):
        stopflag[0] = True
    old_handler = signal.signal(signal.SIGINT, signal_handler)

    print("starting epoch: " + str(start) + "  ending epoch: " + str(start + epochs) + "\n")
    for i in range(start, start + epochs):
        if stopflag[0]:
            break

        error = model.update_fun(*getPieceBatch(pieces)) # pieces dict of len(# midifiles) pieces[name] = array of [noteon, pitch] tuple
        print("\n")
        if i % 100 == 0:
            print "epoch {}, error = {}".format(i, error)

        if i % 500 == 0 or (i % 100 == 0 and i < 1000):
            aPiecesBatch = getPieceSegment(pieces) #16*8 == 128 len sequence x 2 (for each file). So 2 x 128
            xIpt, xOpt = map(numpy.array, aPiecesBatch)
            print(xIpt.shape, xOpt.shape) # xIpt == (128, 78, 80)  xOpt = (128, 78, 2)
            #  80 floats of per-note meta data, 78 possible notes, 128 notes per seq, 10 seqs in a minibatch

            noteStateMatrixToMidi(numpy.concatenate((numpy.expand_dims(xOpt[0], 0),
                                                     model.predict_fun(batch_len, 1, xIpt[0])), axis=0),
                                  'output/sample{}'.format(i))
            pickle.dump(model.learned_config,open('output/params{}.p'.format(i), 'wb'))
    signal.signal(signal.SIGINT, old_handler)
