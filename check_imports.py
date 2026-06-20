import sys
try:
    import streamlit, pandas, matplotlib, seaborn, sweetviz
    print('IMPORTS_OK')
except Exception as e:
    print('IMPORT_ERROR', type(e).__name__, e)
    sys.exit(1)
