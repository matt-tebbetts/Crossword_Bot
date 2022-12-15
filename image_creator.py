import numpy as np
import matplotlib.pyplot as plt
import six

# create function to generate image
def render_mpl_table(data, col_width=2.5, row_height=0.625, font_size=14,
                     header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0, chart_title='Title',
                     ax=None, **kwargs):
    if ax is None:
        # set size of image?
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size)

        # set axis on or off?
        ax.axis('off')

        # set title
        ax.set_title(label=chart_title,
                     fontdict=
                     {'fontsize': 18,
                      # 'fontweight': rcParams['axes.titleweight'],
                      # 'color': rcParams['axes.titlecolor'],
                      'verticalalignment': 'baseline',
                      'horizontalalignment': 'center'}
                     )

    # this makes the dataframe into the "table" image
    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)

    # table details (font size?)
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    # format the lines and edges?
    for k, cell in six.iteritems(mpl_table._cells):
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[k[0] % len(row_colors)])

    # end of function is to return the "ax" variable? why not mpl_table?
    return ax
