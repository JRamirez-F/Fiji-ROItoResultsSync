#@ String(label="Watcher Mode", choices={"Start", "Stop"}, value="Start") mode

"""
This script links selections between the Results Table and ROI Manager.
Selecting a line in the Results Table selects the corresponding ROI, and vice versa.

Press ESC to stop the watchers.
"""

def main():
    from ij import IJ, WindowManager
    from ij.plugin.frame import RoiManager
    from ij.measure import ResultsTable
    from java.util import Timer, TimerTask
    from ij.text import TextWindow
    from java.awt.event import KeyEvent, KeyListener
    from javax.swing import JDialog, JLabel
    import re

    global roi_watcher_active, roi_to_results_active, timer

    # Flags to avoid multiple timers
    if 'roi_watcher_active' not in globals():
        roi_watcher_active = False
    if 'roi_to_results_active' not in globals():
        roi_to_results_active = False

    # Get the ResultsTable window
    tw = WindowManager.getWindow("Results")
    if not isinstance(tw, TextWindow):
        IJ.showMessage("Results table not found.")
        return

    text_panel = tw.getTextPanel()
    rt = ResultsTable.getResultsTable()

    # Store last selections (mutable for watchers)
    last_table_selected = [-1]
    last_roi_selected = [-1]

    def parse_label(label):
        parts = label.split(":")
        if len(parts) < 2:
            return None, None, None
        image = parts[0]
        roi_name = parts[1]
        suffix = ":".join(parts[2:]) if len(parts) > 2 else None
        return image, roi_name, suffix

    def handle_selection_from_table(line):
        label = rt.getLabel(line)
        if label is None or ":" not in label:
            IJ.log("Invalid or missing label: " + str(label))
            return
        win_title, roi_name, _ = parse_label(label)
        if not win_title or not roi_name:
            IJ.log("Unable to parse label: " + str(label))
            return
        img = WindowManager.getImage(win_title)
        if img is None:
            IJ.log("Image window not found for title: " + win_title)
            return
        img.show()
        rm = RoiManager.getInstance()
        if rm is None:
            IJ.log("ROI Manager not found.")
            return
        for i in range(rm.getCount()):
            roi = rm.getRoi(i)
            if roi and roi.getName() == roi_name:
                rm.select(img, i)
                return
        IJ.log("ROI '{}' not found in image '{}'.".format(roi_name, win_title))

    def handle_selection_from_roi(index):
        rm = RoiManager.getInstance()
        if rm is None or index < 0 or index >= rm.getCount():
            return
        roi = rm.getRoi(index)
        if roi is None:
            return
        roi_name = roi.getName().strip()
        slice_z = roi.getZPosition()
        match_idx = -1
        best_fallback = -1
        for row in range(rt.size()):
            label = rt.getLabel(row)
            if label is None:
                continue
            label_img, label_roi, label_suffix = parse_label(label)
            if not label_img or not label_roi:
                continue
            if label_roi.strip() != roi_name:
                continue
            if label_suffix:
                match = re.search(r"z:(\d+)", label_suffix)
                if match:
                    try:
                        label_slice = int(match.group(1))
                        if label_slice == slice_z:
                            match_idx = row
                            break
                    except ValueError:
                        continue
                else:
                    try:
                        if int(label_suffix.strip()) == slice_z:
                            match_idx = row
                            break
                    except:
                        pass
            else:
                best_fallback = row
        if match_idx != -1:
            text_panel.setSelection(match_idx, match_idx)
        elif best_fallback != -1:
            text_panel.setSelection(best_fallback, best_fallback)
        else:
            IJ.log("No results table entry found for ROI name: '{}'".format(roi_name))

    class TableWatcher(TimerTask):
        def run(self):
            try:
                line = text_panel.getSelectionStart()
                if line != last_table_selected[0] and line != -1:
                    last_table_selected[0] = line
                    handle_selection_from_table(line)
            except Exception as e:
                IJ.log("Table watcher error: " + str(e))
                self.cancel()

    class ROIWatcher(TimerTask):
        def run(self):
            try:
                rm = RoiManager.getInstance()
                if rm is None:
                    return
                selected = rm.getSelectedIndexes()
                if selected and selected[0] != last_roi_selected[0]:
                    last_roi_selected[0] = selected[0]
                    handle_selection_from_roi(selected[0])
            except Exception as e:
                IJ.log("ROI watcher error: " + str(e))
                self.cancel()

    class StopWatcherDialog(KeyListener):
        def __init__(self):
            self.dialog = JDialog()
            self.dialog.setTitle("Watcher Running - Press ESC to Stop")
            self.dialog.setSize(300, 100)
            self.dialog.setLocationRelativeTo(None)
            self.dialog.setAlwaysOnTop(True)
            self.dialog.setModal(False)
            self.dialog.setLayout(None)
            label = JLabel("Press ESC to stop the watchers.")
            label.setBounds(40, 20, 250, 40)
            self.dialog.add(label)
            self.dialog.addKeyListener(self)
            self.dialog.setFocusable(True)
            self.dialog.setVisible(True)

        def keyPressed(self, e):
            if e.getKeyCode() == KeyEvent.VK_ESCAPE:
                try:
                    timer.cancel()
                    IJ.log("Watchers stopped by ESC key.")
                except:
                    IJ.log("Failed to stop timer.")
                self.dialog.dispose()
                globals()["roi_watcher_active"] = False
                globals()["roi_to_results_active"] = False

        def keyReleased(self, e): pass
        def keyTyped(self, e): pass

    if mode == "Start":
        if not roi_watcher_active:
            timer = Timer()
            timer.schedule(TableWatcher(), 0, 200)
            roi_watcher_active = True
            IJ.log("Results Table → ROI Manager watcher started.")
        if not roi_to_results_active:
            timer.schedule(ROIWatcher(), 0, 200)
            roi_to_results_active = True
            IJ.log("ROI Manager → Results Table watcher started.")
        else:
            IJ.log("Watchers already running.")
        StopWatcherDialog()
    elif mode == "Stop":
        try:
            timer.cancel()
            IJ.log("Watchers manually stopped.")
        except:
            IJ.log("Failed to stop timer.")
        globals()["roi_watcher_active"] = False
        globals()["roi_to_results_active"] = False

main()
