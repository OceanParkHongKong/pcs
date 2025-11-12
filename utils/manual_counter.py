import tkinter as tk

root = tk.Tk()
root.title("Counter Extraordinaire")

# Settin' up them counters, startin' from the goose egg (0)
left_counter = 0
right_counter = 0

# Function to update the left number
def increment_left(event):
    global left_counter
    left_counter += 1
    left_label.config(text=str(left_counter))

# Function to update the right number
def increment_right(event):
    global right_counter
    right_counter += 1
    right_label.config(text=str(right_counter))

# Settin' up the left label
left_label = tk.Label(root, text="0", font=("Helvetica", 48))
left_label.pack(side="left", expand=True)

# Settin' up the right label
right_label = tk.Label(root, text="0", font=("Helvetica", 48))
right_label.pack(side="right", expand=True)

# Bindin' them keys to the functions
root.bind('<BackSpace>', increment_left)
root.bind('<space>', increment_right)

# Centerin' the window on the screen, slicker than a greased pig
def center_window(width=300, height=200):
    # Get the screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate the position x, y
    x = (screen_width - width) / 2
    y = (screen_height - height) / 2
    root.geometry('%dx%d+%d+%d' % (width, height, x, y))

center_window(500, 100)  # You can adjust these numbers to change the window size

# Function to keep callin' focus_force every 5 seconds
def keep_focus():
    root.focus_force()
    root.after(5000, keep_focus)

# Startin' the keep_focus loop
keep_focus()

# Start the event loop, like startin' the engine on a tractor
root.mainloop()
