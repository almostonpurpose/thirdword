# Meaning Map: Project Progress

## Current Version: V7 (Semantic Gravity Field)

### Version History & Milestones

*   **V1–V5:** Initial explorations into hex-grid layout, Datamuse API integration, and basic semantic "hops."
*   **V6:** Introduced Anchor Sets (exact keyword matching) and basic neighborhood "hits" using a secondary color system.
*   **V7 (Current Breakthrough):**
    *   **Semantic Gravity:** Replaced static grids with a dynamic gravity model. Anchor sets act as satellites at the periphery, pulling relevant words toward them.
    *   **Continuous Field Heatmap:** Implemented a weighted "wider net" color system. Words now display a gradient of heat based on semantic proximity to anchors, even without exact matches.
    *   **Insight Tooltip:** Added backend transparency, showing exact similarity percentages and anchor-pull breakdowns.
    *   **Angular Bias Clustering:** Words are now arranged in rings but biased toward their semantic poles.
    *   **UI Refresh:** Increased scale for readability (32px search, 13px hex labels) and added logic-explainer tooltips for navigation.

### Future Trajectories
*   Implementation of multi-node "Center of Mass" searches.
*   Persistent storage for custom Anchor Sets.
*   Exportable semantic "snapshots" (SVG/JSON).
