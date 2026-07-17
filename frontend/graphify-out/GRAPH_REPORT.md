# Graph Report - frontend  (2026-07-10)

## Corpus Check
- Corpus is ~36,921 words - fits in a single context window. You may not need a graph.

## Summary
- 652 nodes · 917 edges · 53 communities (41 shown, 12 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 27 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48

## God Nodes (most connected - your core abstractions)
1. `cn()` - 69 edges
2. `FileRoutesByPath` - 29 edges
3. `useDashboard()` - 17 edges
4. `compilerOptions` - 17 edges
5. `LoadingSkeleton()` - 9 edges
6. `DashboardContextType` - 9 edges
7. `JobService` - 9 edges
8. `ServiceRegistry` - 8 edges
9. `scripts` - 7 edges
10. `react` - 7 edges

## Surprising Connections (you probably didn't know these)
- `CalendarDayButton()` --references--> `react`  [EXTRACTED]
  src/components/ui/calendar.tsx → package.json
- `useCarousel()` --references--> `react`  [EXTRACTED]
  src/components/ui/carousel.tsx → package.json
- `useChart()` --references--> `react`  [EXTRACTED]
  src/components/ui/chart.tsx → package.json
- `useFormField()` --references--> `react`  [EXTRACTED]
  src/components/ui/form.tsx → package.json
- `useSidebar()` --references--> `react`  [EXTRACTED]
  src/components/ui/sidebar.tsx → package.json

## Import Cycles
- None detected.

## Communities (53 total, 12 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (30): LoadingSkeleton(), StatCard(), StatusBadge(), DashboardContext, DashboardContextType, useDashboard(), ApiAnalyticsService, ApiCompanyService (+22 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (51): dependencies, class-variance-authority, clsx, cmdk, date-fns, embla-carousel-react, @hookform/resolvers, lucide-react (+43 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (38): Input, Separator, SheetContent, SheetContentProps, SheetDescription, SheetFooter(), SheetHeader(), SheetOverlay (+30 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (40): Route, AboutRoute, ContactRoute, DashboardAdminRoute, DashboardAnalyticsRoute, DashboardApplicationsRoute, DashboardCompaniesRoute, DashboardIndexRoute (+32 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (29): devDependencies, eslint, eslint-config-prettier, @eslint/js, eslint-plugin-prettier, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals (+21 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (24): react, Carousel, CarouselApi, CarouselContent, CarouselContext, CarouselContextProps, CarouselItem, CarouselNext (+16 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (20): DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuShortcut(), DropdownMenuSubContent (+12 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (9): LiveMetrics(), MetricItem(), METRICS, Route, SHOWCASE_CARDS, TESTIMONIALS, useCounter(), useInView() (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (11): AccordionContent, AccordionItem, AccordionTrigger, Checkbox, PopoverContent, Progress, ScrollArea, ScrollBar (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleResolution, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (18): aliases, components, hooks, lib, ui, utils, iconLibrary, registries (+10 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (14): Route, Route, Route, Route, Route, Route, Route, Route (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (14): Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator, CommandShortcut() (+6 more)

### Community 13 - "Community 13"
Cohesion: 0.18
Nodes (13): Button, ButtonProps, buttonVariants, Calendar(), CalendarDayButton(), Pagination(), PaginationContent, PaginationEllipsis() (+5 more)

### Community 14 - "Community 14"
Cohesion: 0.19
Nodes (5): DashboardProvider(), Sidebar(), TopBar(), ServiceRegistry, Route

### Community 15 - "Community 15"
Cohesion: 0.19
Nodes (7): SiteFooter(), SiteNav(), LovableErrorOptions, LovableEvents, reportLovableError(), Window, ErrorComponent()

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (11): FormControl, FormDescription, FormFieldContext, FormFieldContextValue, FormItem, FormItemContext, FormItemContextValue, FormLabel (+3 more)

### Community 17 - "Community 17"
Cohesion: 0.27
Nodes (8): consumeLastCapturedError(), renderErrorPage(), fetch(), getServerEntry(), isH3SwallowedErrorBody(), normalizeCatastrophicSsrResponse(), ServerEntry, errorMiddleware

### Community 18 - "Community 18"
Cohesion: 0.20
Nodes (9): ContextMenuCheckboxItem, ContextMenuContent, ContextMenuItem, ContextMenuLabel, ContextMenuRadioItem, ContextMenuSeparator, ContextMenuShortcut(), ContextMenuSubContent (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.22
Nodes (8): AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter(), AlertDialogHeader(), AlertDialogOverlay, AlertDialogTitle

### Community 21 - "Community 21"
Cohesion: 0.22
Nodes (8): Table, TableBody, TableCaption, TableCell, TableFooter, TableHead, TableHeader, TableRow

### Community 22 - "Community 22"
Cohesion: 0.29
Nodes (4): edgeTypes, nodeTypes, PipelineNetworkMap(), Route

### Community 23 - "Community 23"
Cohesion: 0.25
Nodes (7): Breadcrumb, BreadcrumbEllipsis(), BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator()

### Community 24 - "Community 24"
Cohesion: 0.25
Nodes (6): DrawerContent, DrawerDescription, DrawerFooter(), DrawerHeader(), DrawerOverlay, DrawerTitle

### Community 25 - "Community 25"
Cohesion: 0.36
Nodes (5): HoverCardContent, ResizableHandle(), ResizablePanelGroup(), Skeleton(), cn()

### Community 26 - "Community 26"
Cohesion: 0.25
Nodes (7): NavigationMenu, NavigationMenuContent, NavigationMenuIndicator, NavigationMenuList, NavigationMenuTrigger, navigationMenuTriggerStyle, NavigationMenuViewport

### Community 27 - "Community 27"
Cohesion: 0.25
Nodes (7): SelectContent, SelectItem, SelectLabel, SelectScrollDownButton, SelectScrollUpButton, SelectSeparator, SelectTrigger

### Community 28 - "Community 28"
Cohesion: 0.29
Nodes (6): Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle

### Community 29 - "Community 29"
Cohesion: 0.33
Nodes (5): ToggleGroup, ToggleGroupContext, ToggleGroupItem, Toggle, toggleVariants

### Community 30 - "Community 30"
Cohesion: 0.29
Nodes (4): COMPARE, FAQ, PLANS, Route

### Community 31 - "Community 31"
Cohesion: 0.33
Nodes (5): input-otp, InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot

### Community 33 - "Community 33"
Cohesion: 0.40
Nodes (4): Alert, AlertDescription, AlertTitle, alertVariants

### Community 34 - "Community 34"
Cohesion: 0.40
Nodes (4): getRouter(), Register, routeTree, startInstance

### Community 35 - "Community 35"
Cohesion: 0.40
Nodes (3): PILLARS, Route, STEPS

### Community 39 - "Community 39"
Cohesion: 0.50
Nodes (3): Avatar, AvatarFallback, AvatarImage

### Community 40 - "Community 40"
Cohesion: 0.67
Nodes (3): Badge(), BadgeProps, badgeVariants

### Community 41 - "Community 41"
Cohesion: 0.50
Nodes (3): TabsContent, TabsList, TabsTrigger

## Knowledge Gaps
- **344 isolated node(s):** `$schema`, `style`, `rsc`, `tsx`, `css` (+339 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `cn()` connect `Community 25` to `Community 2`, `Community 5`, `Community 6`, `Community 8`, `Community 12`, `Community 13`, `Community 16`, `Community 18`, `Community 20`, `Community 21`, `Community 23`, `Community 24`, `Community 26`, `Community 27`, `Community 28`, `Community 29`, `Community 31`, `Community 33`, `Community 39`, `Community 40`, `Community 41`, `Community 44`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `dependencies` connect `Community 1` to `Community 37`, `Community 4`, `Community 5`, `Community 31`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `react` connect `Community 5` to `Community 1`, `Community 2`, `Community 13`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **What connects `$schema`, `style`, `rsc` to the rest of the system?**
  _344 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07456140350877193 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.0392156862745098 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.05391120507399577 - nodes in this community are weakly interconnected._