# Western Refrigeration replica

Static replica of https://westernequipments.com/, captured October 18, 2026. Original public HTML, responsive CSS, images, fonts and presentation JavaScript are retained for visual fidelity. Pages and presentation assets are served locally from `dist/`.

## Preview

Run `python -m http.server 8080 --directory dist`, then open http://localhost:8080.

## Behavior

Navigation, product pages, sliders, responsive menus, tabs and galleries retain the original presentation scripts. Search uses the local page index. Enquiry and application forms do not send information: submitting a valid form displays an explicit replica notice. WordPress administration, commerce, server-side filtering, and email delivery are not replicated. Some uncaptured archive, pagination, and secondary routes open the original site. Third-party social links remain external.

`mirror.py` captures public source and assets, excluding analytics scripts. `.capture/` is an ignored download cache. The capture report records page and asset counts and upstream failures. Source content and brand assets belong to their respective owners.
