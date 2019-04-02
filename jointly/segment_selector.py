from matplotlib import pyplot as plt
import pandas as pd

class SegmentSelector:

    cur_plot = None

    def __init__(self, signals, segments=None):
        self.signals = signals
        self.segments = segments
        if segments is None:
            self.segments = {
                signal: {
                    'first': {},
                    'second': {},
                } for signal in signals.columns
            }
        self._display_plots()
    
    def _display_plots(self):
        nrows = len(self.signals.columns)
        ncols = 1
        fig, axes = plt.subplots(nrows, ncols, figsize=(10, nrows*7))
        
        for index, name in enumerate(self.signals.columns):
            axes[index].set_title(name)
            axes[index].plot(self.signals[name].interpolate(method='time').values)
        fig.tight_layout()

        bp_id = fig.canvas.mpl_connect('button_press_event', self._on_click)

    def _display_segments(self):
        print('Do')

    def _on_click(self, event):
        #if not event.dblclick:
        #    return
        if not event.inaxes:
            return
        self.event = event
        title = event.inaxes.title.get_text()
        index = int(event.xdata)
        
        for segment in ['first', 'second']:
            for time in ['start', 'end']:
                if time not in self.segments[title][segment]:
                    self.segments[title][segment][time] = self.signals.index[index]
                    break
            else:
                continue
            break
        
        self._display_segments()
            

