def test_plugin_accessible(application):
    hasattr(application, "sample")
