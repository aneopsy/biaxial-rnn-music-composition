import midi
import numpy

lowerBound = 24
upperBound = 102

def midi2note(midi):
    ''' convert midi note number to note name, e.g. [0, 127] -> [C-1, G9]'''
    if type(midi) != int:
        raise TypeError, "an integer is required, got %s" % midi
    if not (-1 < midi < 128):
        raise ValueError, "an integer between 0 and 127 is excepted, got %d" % midi
    midi = int(midi)
    _valid_notenames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    return _valid_notenames[midi % 12] + str( midi / 12 - 1)


def midiToNoteStateMatrix(midifile):

    inputMidiFile = midi.read_midifile(midifile)

    # track[0] is the midi.TrackNameEvent which has tick info, there can be 8 tracks
    timeleft = [track[0].tick for track in inputMidiFile]
    print("# tracks: " + str(len(timeleft)))
    noteCountHistogram = numpy.zeros(upperBound)

    posns = [0 for track in inputMidiFile]

    statematrix = []
    span = upperBound - lowerBound   #range of midi pitches (restrict range)
    time = 0

    state = [[0, 0] for x in range(span)] # state == pairs of tuples len(range of midi pitches) long, i.e. 78 pitches!
    statematrix.append(state)
    while True:
        if time % (inputMidiFile.resolution / 4) == (inputMidiFile.resolution / 8):
            # Crossed a note boundary. Create a new state, defaulting to holding notes
            oldstate = state
            state = [[oldstate[x][0],0] for x in range(span)]
            statematrix.append(state)

        for i in range(len(timeleft)):  # for each of the 8 tracks (len(timeleft)) #i == index of 8 tracks
            while timeleft[i] == 0:
                track = inputMidiFile[i]
                pos = posns[i]  #pos is index on each tracks events:

                evt = track[pos]
                if isinstance(evt, midi.NoteEvent):
                    if (evt.pitch < lowerBound) or (evt.pitch >= upperBound):
                        print "Note {} at time {} out of bounds (ignoring)".format(evt.pitch, time)
                        pass
                    else:
                        # print(midi2note(evt.pitch))
                        if isinstance(evt, midi.NoteOffEvent) or evt.velocity == 0:
                            state[evt.pitch - lowerBound] = [0, 0]
                        else:
                            noteCountHistogram[evt.pitch] += 1
                            state[evt.pitch - lowerBound] = [1, 1]
                elif isinstance(evt, midi.TimeSignatureEvent):
                    if evt.numerator not in (2, 4):
                        # We don't want to worry about non-4 time signatures. Bail early!
                        print "Found time signature event {}. Bailing!".format(evt)
                        print (noteCountHistogram, len(noteCountHistogram))
                        return statematrix
                    else:
                        print("Time Signature: " + str(evt.numerator) + " ")

                try:
                    # print("[IOHAVOC] ingesting track # " + str(i))
                    # print("posns: " + str(posns))
                    timeleft[i] = track[pos + 1].tick
                    # print("timeleft[i] " + str(timeleft[i]))
                    posns[i] += 1
                except IndexError:
                    timeleft[i] = None

            if timeleft[i] is not None:
                timeleft[i] -= 1

        if all(t is None for t in timeleft):
            break

        time += 1

    print("time ticks/PPQ: " + str(time) + "  i.e. beats: " + str(time/480) + "  i.e 4/4 measures: " + str(time/480/4))
    # print(noteCountHistogram)
    print("Statematrix shape, length: " + str(statematrix.__len__()) + " each with " + str(statematrix[0].__len__()) + " notes")
    return statematrix



def noteStateMatrixToMidi(statematrix, name="example"):
    statematrix = numpy.asarray(statematrix)
    pattern = midi.Pattern()
    track = midi.Track()
    pattern.append(track)
    
    span = upperBound - lowerBound  #range of midi pitches (restrict range)
    tickscale = 55

    lastcmdtime = 0
    prevstate = [[0,0] for x in range(span)]
    for time, state in enumerate(statematrix + [prevstate[:]]):  
        offNotes = []
        onNotes = []
        for i in range(span):
            n = state[i]
            p = prevstate[i]
            if p[0] == 1:
                if n[0] == 0:
                    offNotes.append(i)
                elif n[1] == 1:
                    offNotes.append(i)
                    onNotes.append(i)
            elif n[0] == 1:
                onNotes.append(i)
        for note in offNotes:
            track.append(midi.NoteOffEvent(tick=(time-lastcmdtime)*tickscale, pitch=note+lowerBound))
            lastcmdtime = time
        for note in onNotes:
            track.append(midi.NoteOnEvent(tick=(time-lastcmdtime)*tickscale, velocity=40, pitch=note+lowerBound))
            lastcmdtime = time
            
        prevstate = state
    
    eot = midi.EndOfTrackEvent(tick=1)
    track.append(eot)

    midi.write_midifile("{}.mid".format(name), pattern)