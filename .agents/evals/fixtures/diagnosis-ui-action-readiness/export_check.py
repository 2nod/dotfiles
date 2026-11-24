def check_export(panel):
    panel.click('Open summary')
    panel.wait_for_text('Monthly summary')
    panel.click('Export CSV')
