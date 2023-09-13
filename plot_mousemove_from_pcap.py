#!/usr/bin/env python
import numpy as np
import pandas as pd
import sys
import matplotlib.pyplot as plt


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <wireshark csv file>")
        sys.exit(0)

    df = pd.read_csv(sys.argv[1], index_col=0)

    x_axis = np.cumsum(df["X Axis"].dropna().reset_index(drop=True))
    y_axis = np.cumsum(df["Y Axis"].dropna().reset_index(drop=True))

    plt.plot(x_axis, y_axis)
    plt.show()


if __name__ == "__main__":
    main()
