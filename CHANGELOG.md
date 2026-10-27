# Changelog

## 0.1.0 (2026-10-27)


### Features

* **api:** serve the inbox over HTTP with runs, sources and a schedule ([#13](https://github.com/bhoudebert/lookout/issues/13)) ([e8097a8](https://github.com/bhoudebert/lookout/commit/e8097a8790252e42ab90b965ae158903af491d6b))
* **categories:** a page to define categories and kinds, and file existing items again ([#30](https://github.com/bhoudebert/lookout/issues/30)) ([c621ef0](https://github.com/bhoudebert/lookout/commit/c621ef01bca6854f921fd3c1121704b71ff72018))
* **categories:** give each category an emoji icon the local model suggests ([#55](https://github.com/bhoudebert/lookout/issues/55)) ([ce4536a](https://github.com/bhoudebert/lookout/commit/ce4536ab0015ef70957ae479c153fede6467c0da))
* **categories:** move a category and show the parents of flat paths ([#32](https://github.com/bhoudebert/lookout/issues/32)) ([a707a1f](https://github.com/bhoudebert/lookout/commit/a707a1fe77a9d9515670dc7f6345d22abac79dcb))
* **categories:** one hierarchical category with a tree beside the inbox ([#31](https://github.com/bhoudebert/lookout/issues/31)) ([0882151](https://github.com/bhoudebert/lookout/commit/08821511dc98885b55fecad56ca5896a898297dd))
* **channels:** file items by topic and by kind, with author and article tags ([#28](https://github.com/bhoudebert/lookout/issues/28)) ([c830cbe](https://github.com/bhoudebert/lookout/commit/c830cbe6620aa8a7ac695528ab4ed04aab8213b9))
* **cli:** load lookout.yaml and add run, inbox, act, doctor, demo, reassess and export ([#10](https://github.com/bhoudebert/lookout/issues/10)) ([f661e2e](https://github.com/bhoudebert/lookout/commit/f661e2e080defe6606368afcd4049adff0aebdc9))
* **dashboard:** dense aligned inbox rows and a structured categories page ([#34](https://github.com/bhoudebert/lookout/issues/34)) ([6492cf1](https://github.com/bhoudebert/lookout/commit/6492cf1236f71b7b3260bb76af39e63e132d48b0))
* **dashboard:** offer to search everything when a search is limited to a view ([#41](https://github.com/bhoudebert/lookout/issues/41)) ([99983c5](https://github.com/bhoudebert/lookout/commit/99983c5964b56eb9446778818d2769cbc184bd22))
* **dashboard:** one frame, view tabs and a last-run strip for the inbox ([#62](https://github.com/bhoudebert/lookout/issues/62)) ([b841195](https://github.com/bhoudebert/lookout/commit/b841195a63d79df8ef8c2f694fd76273ba95241c))
* **dashboard:** resizable, wider list; new favicon; website and guide in the dashboard design ([#65](https://github.com/bhoudebert/lookout/issues/65)) ([977a4d4](https://github.com/bhoudebert/lookout/commit/977a4d425f1faa3202af8fcf74418f6572fff924))
* **dashboard:** show each item in the panel as j and k move ([#52](https://github.com/bhoudebert/lookout/issues/52)) ([7b29da6](https://github.com/bhoudebert/lookout/commit/7b29da6af830575f74b0a2e258a8203bf763123c))
* **design:** adopt the samurai calm design in the dashboard, the guide and the website ([#47](https://github.com/bhoudebert/lookout/issues/47)) ([5508f75](https://github.com/bhoudebert/lookout/commit/5508f75706d41ddd719d7e934d9bd93e50d4ceff))
* **digest:** condense a selection into a dense, cited digest with a model of its own ([#57](https://github.com/bhoudebert/lookout/issues/57)) ([13fa2a5](https://github.com/bhoudebert/lookout/commit/13fa2a506b10ecb3d0b42abb29f28eeee1a35107))
* **digest:** list pending and written digests with the days their items were published ([#63](https://github.com/bhoudebert/lookout/issues/63)) ([b4aee02](https://github.com/bhoudebert/lookout/commit/b4aee02eb537e6cefc8139ea4ec3a2bdeb12083b))
* **digest:** write digests in the background, bounded, with pending state and cancel ([#59](https://github.com/bhoudebert/lookout/issues/59)) ([ce7572f](https://github.com/bhoudebert/lookout/commit/ce7572f6d8e964d1e4ed38f175ca7c4c0ad6e7df))
* **domain:** add item lifecycle, priority policy, stack match and SQLite store ([#8](https://github.com/bhoudebert/lookout/issues/8)) ([334a184](https://github.com/bhoudebert/lookout/commit/334a1846a7ee7d7e25bbf919d1ceaa6b181105b1))
* **github:** read releases, security advisories and Dependabot alerts ([#19](https://github.com/bhoudebert/lookout/issues/19)) ([6be0c2a](https://github.com/bhoudebert/lookout/commit/6be0c2ab1092065601589b36f3176f993dba6899))
* **osv:** follow vulnerabilities of the declared stack with CISA exploitation ([#23](https://github.com/bhoudebert/lookout/issues/23)) ([b91fad8](https://github.com/bhoudebert/lookout/commit/b91fad8df8793c498f3e613abea78bb9c59d0fca))
* **personalization:** ratings judge content not source, and the model sees them ([#56](https://github.com/bhoudebert/lookout/issues/56)) ([8aaca1d](https://github.com/bhoudebert/lookout/commit/8aaca1dc589c06754418363f96dc91e4e4012aad))
* **retention:** keep the inbox small with freshness, expiry, two orders and paging ([#37](https://github.com/bhoudebert/lookout/issues/37)) ([28b6924](https://github.com/bhoudebert/lookout/commit/28b6924297a987444d5dfc0969729ddd56168ea6))
* **sources:** add Hacker News and one-click suggested sources ([#35](https://github.com/bhoudebert/lookout/issues/35)) ([e29cad4](https://github.com/bhoudebert/lookout/commit/e29cad47be3d4ff7cfe9f48aa8d8878001d5f005))
* **sources:** add Reddit and YouTube sources and suggested sources by theme ([#39](https://github.com/bhoudebert/lookout/issues/39)) ([b8428fe](https://github.com/bhoudebert/lookout/commit/b8428febad0ac4549f126daf3b1249f7de42f0cf))
* **sources:** ingest RSS and Atom feeds and enrich items through any OpenAI-compatible model ([#9](https://github.com/bhoudebert/lookout/issues/9)) ([5b4fc86](https://github.com/bhoudebert/lookout/commit/5b4fc86fa254f44db71b36af8d86d70503b254cf))
* **sources:** keywords match whole words, and suggest the Dealabs deal feeds ([#53](https://github.com/bhoudebert/lookout/issues/53)) ([86be811](https://github.com/bhoudebert/lookout/commit/86be811d1fc075db004c6b67c29fedb53c6aa90f))
* **sources:** let a source name the model that reads its items ([#68](https://github.com/bhoudebert/lookout/issues/68)) ([4cacae8](https://github.com/bhoudebert/lookout/commit/4cacae8ac9abdf37129432785a4e898e26c968f8))
* **sources:** manage sources and channels from the dashboard ([#29](https://github.com/bhoudebert/lookout/issues/29)) ([b827b67](https://github.com/bhoudebert/lookout/commit/b827b67fe0c6fb830e50bcb8e24b4f1012f671c0))
* **sources:** say where items go and create a category from the source form ([#40](https://github.com/bhoudebert/lookout/issues/40)) ([318fa2b](https://github.com/bhoudebert/lookout/commit/318fa2bb65df3054b2f0ec495eec03536eeb344b))
* **triage:** learn from actions and explain every rank ([#12](https://github.com/bhoudebert/lookout/issues/12)) ([906b795](https://github.com/bhoudebert/lookout/commit/906b795a81a221d849ed5109ec811ce33c0058d0))
* **triage:** rate a whole selection or a whole filter up or down ([#51](https://github.com/bhoudebert/lookout/issues/51)) ([41cc5e1](https://github.com/bhoudebert/lookout/commit/41cc5e1148d9031b5606c47d85a33762f03c4637))
* **triage:** thumbs up and down on every item, and Done that only clears ([#50](https://github.com/bhoudebert/lookout/issues/50)) ([3934ce8](https://github.com/bhoudebert/lookout/commit/3934ce89a670c8d2a602a852a1bcb48133aa188b))
* **ui:** add the dashboard with keyboard triage, bulk actions and journeys ([#14](https://github.com/bhoudebert/lookout/issues/14)) ([6091433](https://github.com/bhoudebert/lookout/commit/6091433a38cf934d7ec35b5e76a1e79351b4be05))


### Bug fixes

* **categories:** create missing parents and revamp the inbox layout ([#33](https://github.com/bhoudebert/lookout/issues/33)) ([1be2f8f](https://github.com/bhoudebert/lookout/commit/1be2f8f5ab84b5f851bb9bab3d2ae6771c6685e3))
* **categories:** unread items wait in the category their source names, not in Other ([#67](https://github.com/bhoudebert/lookout/issues/67)) ([7f236a0](https://github.com/bhoudebert/lookout/commit/7f236a017fb17a3e260104f6f5d0eb5e37ec5f14))
* **cli:** accept a model Ollama lists with its latest tag ([#27](https://github.com/bhoudebert/lookout/issues/27)) ([e5f6363](https://github.com/bhoudebert/lookout/commit/e5f63632a5d4344738ee1a308eacab040b2fef84))
* **dashboard:** lay out the item detail panel properly ([#43](https://github.com/bhoudebert/lookout/issues/43)) ([66e715a](https://github.com/bhoudebert/lookout/commit/66e715a036e3af1e421d81bbb9ed77acc2994122))
* **dashboard:** make the category counts match what the list shows ([#38](https://github.com/bhoudebert/lookout/issues/38)) ([2da7355](https://github.com/bhoudebert/lookout/commit/2da73552c19272e60bc2797533076ae2a36fe328))
* **dashboard:** make the list's resize bar inert under dialogs, and cover more of the UI in journeys ([#66](https://github.com/bhoudebert/lookout/issues/66)) ([854b8df](https://github.com/bhoudebert/lookout/commit/854b8dfc3ad1170cda85f2134f1f35532d85795b))
* **digest:** cover every item, and ask again about the ones the model skips ([#60](https://github.com/bhoudebert/lookout/issues/60)) ([33cb5d7](https://github.com/bhoudebert/lookout/commit/33cb5d794cab841a8a50b54cff1585a4ce858d6e))
* **digest:** write big categories in calls of 40 items, grouped by theme, then merge ([#61](https://github.com/bhoudebert/lookout/issues/61)) ([22a1826](https://github.com/bhoudebert/lookout/commit/22a182620d4dd0d62342c8bff6944099326b71ac))
* **enrichment:** spend the model budget only on items that can be seen ([#49](https://github.com/bhoudebert/lookout/issues/49)) ([5900a88](https://github.com/bhoudebert/lookout/commit/5900a88fa7cd38139fe420dc3fd44d0ea1d78f3c))
* **security:** refuse non-web item links, hide secrets in errors, escape LIKE, tighten repo names ([#54](https://github.com/bhoudebert/lookout/issues/54)) ([c0b503f](https://github.com/bhoudebert/lookout/commit/c0b503f71d06da8e4b0b950e675efd578ee58252))
* **sources:** accept a GitHub repository written as an address ([#36](https://github.com/bhoudebert/lookout/issues/36)) ([4c12a86](https://github.com/bhoudebert/lookout/commit/4c12a868ed89512a3b499434f9fdaad6b434f6bd))
* **sources:** offer Lobsters newest as well as hottest, and fix the favicons ([#48](https://github.com/bhoudebert/lookout/issues/48)) ([7938b31](https://github.com/bhoudebert/lookout/commit/7938b3137acc3c782302c08ada59f9dc4ee14f9b))


### Documentation

* add governance, ADRs and specs ([#1](https://github.com/bhoudebert/lookout/issues/1)) ([6c6e7b3](https://github.com/bhoudebert/lookout/commit/6c6e7b38b45f0e34b3801a2aa58bec59045acf03))
* **guide:** explain local model context, memory and speed ([#58](https://github.com/bhoudebert/lookout/issues/58)) ([73da70c](https://github.com/bhoudebert/lookout/commit/73da70c9d6499f38a6e33d205620eafc6a24be65))
* **guide:** say how to get and size the recommended reading model ([#70](https://github.com/bhoudebert/lookout/issues/70)) ([14892cc](https://github.com/bhoudebert/lookout/commit/14892ccbf9513f9aa9b255f62fe2bbb9f698383a))
* **guide:** which local model reads best, from a 1000-item benchmark ([#69](https://github.com/bhoudebert/lookout/issues/69)) ([a88da22](https://github.com/bhoudebert/lookout/commit/a88da2296b3cb015f6a40144be6b3de59b439779))
* **site:** add the user guide, the website and the Pages workflow ([#18](https://github.com/bhoudebert/lookout/issues/18)) ([24ba6a7](https://github.com/bhoudebert/lookout/commit/24ba6a721a74e143470f7639608bcec7caaef7e2))


### Build and tooling

* add Nix shell, Python tooling, quality gate and CI ([#2](https://github.com/bhoudebert/lookout/issues/2)) ([ebf6085](https://github.com/bhoudebert/lookout/commit/ebf60857c87ce90883f1f65595f64b2fbddf6f0e))
* **docker:** publish a container image and a NixOS module ([#24](https://github.com/bhoudebert/lookout/issues/24)) ([d8a93ac](https://github.com/bhoudebert/lookout/commit/d8a93acd31dec9d0702a517b806bac356e14b3ff))
* **nix:** add runnable apps for the CLI, the server and the demo ([#26](https://github.com/bhoudebert/lookout/issues/26)) ([3fbd4ac](https://github.com/bhoudebert/lookout/commit/3fbd4aca215a26d154bd6c668240e0eb6a137d9d))
* **nix:** load the dev shell with direnv ([#25](https://github.com/bhoudebert/lookout/issues/25)) ([f43e87b](https://github.com/bhoudebert/lookout/commit/f43e87b697c612595a405f62bf35954d947c05d1))
