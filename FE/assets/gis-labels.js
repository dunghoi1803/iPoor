(() => {
  const EMPTY_STRING = "";
  const GEO_VERSION_63 = "old_63";
  const GEO_VERSION_34 = "new_34";
  const JSON_63_PATH = "../data/processed/geo_labels_63.json";
  const JSON_34_PATH = "../data/processed/geo_labels_34.json";
  const LEADING_ZERO_REGEX = /^0+/;
  const GEO_CODE_PAD_LENGTH = 2;
  const CACHE = new Map();

  function normalizeGeoCode(rawCode) {
    if (rawCode === null || rawCode === undefined) return EMPTY_STRING;
    const raw = String(rawCode).trim();
    if (!raw) return EMPTY_STRING;
    const trimmed = raw.replace(LEADING_ZERO_REGEX, EMPTY_STRING);
    if (trimmed) return trimmed;
    return raw;
  }

  function getJsonPath(geoVersion) {
    if (geoVersion === GEO_VERSION_34) return JSON_34_PATH;
    return JSON_63_PATH;
  }

  function buildLabelMap(payload) {
    const map = new Map();
    if (!payload) return map;
    Object.entries(payload).forEach(([key, value]) => {
      if (key && value) {
        map.set(key, value);
      }
    });
    return map;
  }

  function getProvinceName(labelMap, geoCode) {
    if (!labelMap || !geoCode) return EMPTY_STRING;
    const raw = normalizeGeoCode(geoCode);
    if (!raw) return EMPTY_STRING;
    if (labelMap.has(raw)) return labelMap.get(raw);
    const padded = raw.padStart(GEO_CODE_PAD_LENGTH, "0");
    if (labelMap.has(padded)) return labelMap.get(padded);
    return EMPTY_STRING;
  }

  async function loadProvinceLabelMap(geoVersion) {
    const version = geoVersion || GEO_VERSION_63;
    if (CACHE.has(version)) return CACHE.get(version);
    const path = getJsonPath(version);
    const res = await fetch(encodeURI(path));
    if (!res.ok) {
      CACHE.set(version, new Map());
      return CACHE.get(version);
    }
    const payload = await res.json();
    const map = buildLabelMap(payload);
    CACHE.set(version, map);
    return map;
  }

  window.GisLabelHelper = {
    loadProvinceLabelMap,
    getProvinceName,
  };
})();
