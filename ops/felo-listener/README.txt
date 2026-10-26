FELO LISTENER - say "Hey Felo" on the work PC

INSTALL (once):
  1. Unzip this folder anywhere (for example Downloads\felo-listener).
  2. Open PowerShell in that folder (Shift + right-click inside the folder > "Open PowerShell window here").
  3. Run:   powershell -ExecutionPolicy Bypass -File .\install.ps1
  It installs Python if needed, sets everything up, and starts the listener now and at every Windows log-in.

USE:
  Say "Hey Felo" (or "Oye Felo"), wait for the beep, then ask. Felo answers through the speakers.
  Keep talking for a follow-up; say "stop" or "bye" to end.
  "Hey Felo, stop listening" pauses it; "Hey Felo, start listening" resumes.
  Works best: "Hey Felo" ... short pause ... your question.

PRIVACY: the microphone is checked only on this PC. Nothing leaves the PC until it hears "Hey Felo".

CHECK / FIX:
  Log:            %LOCALAPPDATA%\FeloListener\felo-listener.log
  Wrong mic?      open PowerShell in %LOCALAPPDATA%\FeloListener and run:
                    .\venv\Scripts\python.exe felo_listener.py --devices
                  then tell Claude the microphone number.
  Mic test:       .\venv\Scripts\python.exe felo_listener.py --level    (shows the wake score while you speak)
  Stop:           Stop-ScheduledTask -TaskName 'Felo Listener'
  Remove:         Unregister-ScheduledTask -TaskName 'Felo Listener' -Confirm:$false
