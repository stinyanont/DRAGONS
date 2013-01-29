class NIRI_DARK(DataClassification):
    name="NIRI_DARK"
    usage = """
        Applies to all dark datasets from the NIRI instrument
        """
    parent = "NIRI"
    requirement = PHU(OBSTYPE="DARK")

newtypes.append(NIRI_DARK())
