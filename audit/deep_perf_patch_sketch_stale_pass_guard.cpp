// PATCH SKETCH ONLY - not in the tree, not compiled, not deployed.
// Companion to deep_perf_study_20261124.md, section B.
// Would live as src/EngineFixes/StaleRenderPassGuard.{h,cpp} in the Community Shaders fork.
//
// Purpose: stop the recurring AV at SkyrimSE.exe+14F3E4A (ID 107644+0x8A, `call [rax+0x10]`, rax = 0):
// BSBatchRenderer::RenderPassImmediately calls pass->shader->SetupTechnique() on a BSRenderPass whose
// `shader` field no longer points at a BSShader (both logged crashes: it points at heap memory 0xAA0 /
// 0x1D60 bytes from the pass itself, first qword zero).
//
// Two layers:
//   1. Per-draw guard at the shared call site RenderBatches -> RenderPassImmediately
//      (ID 107642 + 0x28F on AE 1.6.1170, SE 100852 + 0x29E). Drops the one pass.
//   2. Chain sanitiser in a detour of BSBatchRenderer::RenderBatches (ID 107642), because after a bad
//      pass the engine still executes `mov rbx,[rbx+0x30]` (pass->passGroupNext, 107642+0x294) and
//      walks whatever the stale pass links to. Layer 2 cuts the list before the engine walks it.
//
// Install LAST among our thunks on this site (after FurShells, LightLimitFix, InteriorSun,
// TerrainBlending, NeuralRendering) so it is the outermost of ours and runs before they read the pass.
// SPS installs its own thunk at kDataLoaded and will still sit outside ours.

#include <atomic>

namespace StaleRenderPassGuard
{
	// Image range of SkyrimSE.exe; every BSShader vtable lives inside it.
	inline std::uintptr_t g_imageBegin = 0;
	inline std::uintptr_t g_imageEnd = 0;
	inline std::atomic<std::uint32_t> g_dropped{ 0 };
	inline std::atomic<std::uint32_t> g_cut{ 0 };

	inline void Init()
	{
		const auto base = REL::Module::get().base();
		const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
		const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(base + dos->e_lfanew);
		g_imageBegin = base;
		g_imageEnd = base + nt->OptionalHeader.SizeOfImage;
	}

	// SEH keeps this safe if the pass or its shader pointer is unreadable. No C++ objects with
	// destructors may live in this function (MSVC C2712).
	inline bool PassLooksValid(const RE::BSRenderPass* a_pass) noexcept
	{
		__try {
			if (!a_pass)
				return false;
			const auto* shader = a_pass->shader;
			if (!shader || !a_pass->geometry)
				return false;
			const auto vtbl = *reinterpret_cast<const std::uintptr_t*>(shader);
			return vtbl >= g_imageBegin && vtbl < g_imageEnd;
		} __except (EXCEPTION_EXECUTE_HANDLER) {
			return false;
		}
	}

	// Layer 1: call site 107642+0x28F (and optionally 107673+0x1EE, 107667+0xED, where LightLimitFix
	// already hooks RenderPass1/RenderPass3).
	struct BSBatchRenderer_RenderPassImmediately
	{
		static void thunk(RE::BSRenderPass* a_pass, uint32_t a_technique, bool a_alphaTest, uint32_t a_renderFlags)
		{
			if (!PassLooksValid(a_pass)) [[unlikely]] {
				if (g_dropped.fetch_add(1, std::memory_order_relaxed) < 32)
					logger::warn("[StaleRenderPassGuard] dropped pass {:p} technique {:X} flags {:X}", static_cast<const void*>(a_pass), a_technique, a_renderFlags);
				return;
			}
			func(a_pass, a_technique, a_alphaTest, a_renderFlags);
		}
		static inline REL::Relocation<decltype(thunk)> func;
	};

	// Layer 2: detour of BSBatchRenderer::RenderBatches (ID 107642 / SE 100852). FrameAnnotations
	// already detours this function behind a setting and SPS detours it when shadow instancing is on,
	// so a third detour is known to coexist. Signature as used by both:
	//   bool (BSBatchRenderer*, uint32_t* technique, uint32_t* groupIndex, void* passIndexList, uint32_t renderFlags)
	struct BSBatchRenderer_RenderBatches
	{
		static bool thunk(RE::BSBatchRenderer* a_this, uint32_t* a_technique, uint32_t* a_groupIndex, void* a_list, uint32_t a_renderFlags)
		{
			// renderPass / renderPassMap are CommonLibSSE-NG members (BSBatchRenderer.h, 0x008 / 0x020).
			// VERIFY before use: the map lookup the engine does is m_RenderPassMap.get(technique).
			if (a_this && a_technique && a_groupIndex && *a_groupIndex < 5) {
				if (const auto it = a_this->renderPassMap.find(*a_technique); it != a_this->renderPassMap.end()) {
					if (auto* group = a_this->renderPass[it->second]) {
						RE::BSRenderPass** link = &group->passes[*a_groupIndex];
						// Bounded walk: a looped stale chain must not hang the frame.
						for (std::uint32_t n = 0; *link && n < 65536; ++n) {
							if (!PassLooksValid(*link)) [[unlikely]] {
								*link = nullptr;  // cut here; the memory is owned (and freed) elsewhere
								g_cut.fetch_add(1, std::memory_order_relaxed);
								break;
							}
							link = &(*link)->passGroupNext;
						}
					}
				}
			}
			return func(a_this, a_technique, a_groupIndex, a_list, a_renderFlags);
		}
		static inline REL::Relocation<decltype(thunk)> func;
	};

	inline void Install()
	{
		Init();
		stl::write_thunk_call<BSBatchRenderer_RenderPassImmediately>(REL::RelocationID(100852, 107642).address() + REL::Relocate(0x29E, 0x28F));
		// Optional second layer, behind a setting until it has soaked:
		// stl::detour_thunk<BSBatchRenderer_RenderBatches>(REL::RelocationID(100852, 107642));
	}
}

// Open points before this could ship:
//  - Layer 1 alone does not protect the engine's own `mov rbx,[rbx+0x30]` if the stale pass links to
//    unreadable memory. In both logged crashes the stale pass itself was readable.
//  - The vtable-in-image test rejects a BSShader subclass defined by another DLL. None is known in this
//    load order (all shaders are engine singletons), but log the first drops and check.
//  - This hides a use-after-free; it does not fix it. Keep the log line and a counter in the overlay so
//    the next occurrence names the geometry (read a_pass->geometry->name under the same SEH block).
