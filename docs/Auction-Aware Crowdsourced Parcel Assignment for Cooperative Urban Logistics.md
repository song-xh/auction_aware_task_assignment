JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
# Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics
Guanglei Zhu, Jiawen Zhang, Shuo He, Xuhui Song, Yafei Li, Jiangliang Xu, Mingliang Xu 
Abstract—The rapid growth of e-commerce and mobile internet has created significant opportunities for crowdsourced First and Last Mile Logistics (FLML) services. In these services, couriers can collect pick-up parcels while delivering drop-off parcels. Recently, an emerging service paradigm involving parcel sharing across multiple platforms has gained traction, effectively addressing the issue of uneven parcel distribution in independent platforms. However, two key challenges remain: (i) incentivizing cooperating platforms and their couriers to participate in crossplatform parcel assignment, and (ii) adaptively optimizing parcel assignments to maximize overall revenue. In this paper, we investigate the novel Cross-Platform Urban Logistics (CPUL) problem, which seeks to identify optimal courier assignments for pick-up parcels in a cooperative framework. To encourage participation in cross-platform parcel sharing, we propose a doublelayer auction model that integrates a First-Price Sealed Auction for cross-platform couriers with a Reverse Vickrey Auction for cooperating platforms. Additionally, we introduce a cross-aware parcel assignment framework to address the CPUL problem by maximizing revenue for the local platform. This framework employs a dynamic threshold-based parcel assignment method, which allocates parcels to a shared pool for cross-task matching based on adaptive thresholds. It further incorporates a dual-stage adaptive optimization strategy to determine optimal batch sizes and decide whether parcels are assigned locally or cooperatively within each batch. Extensive experiments on two real-world datasets demonstrate the effectiveness and efficiency of the proposed methods. 
Index Terms—Location-based service, task assignment, auction model, cross-platform service, urban logistics. 
# I. INTRODUCTION
W ITH the rapid development of e-commerce and spatialcrowdsourcing technologies, crowdsourced urban lo- crowdsourcing technologies，crowdsourced urban logistics has emerged as an efficient and cost-effective solution to address the dynamic and complex urban logistics. Urban logistics systems typically provide two core services under the framework of First and Last Mile Logistics (FLML in short): first-mile logistics, which involves transporting customer parcels to transfer stations; and last-mile logistics, which delivers parcels from transfer stations to customers [1], [2], [3]. In this operational framework, couriers depart from transfer stations with parcels destined for customers. Concurrently, the logistics platform dynamically assigns suitable couriers to collect parcels based on real-time conditions. Owing to its 
This work is supported by the following grants: NSFC Grants 62372416, 62325602, 62402453, 62036010, and 61972362; HNSF Grant 242300421215. G. Zhu, J. Zhang, Shuo. He, X. Song, Y. Li and M. Xu are with the School of Computer Science and Artificial Intelligence, Zhengzhou University, Zhengzhou, China. (e-mail: {csglzhu, heshuo, ieyfli, iexumingliang}@zzu.edu.cn, {zjw0308, xhsong}@gs.zzu.edu.cn) J. Xu is with the Department of Computer Science, Hong Kong Baptist University, Hong Kong SAR, China. (e-mail: xujl@comp.hkbu.edu.hk). 
significant contributions to enhancing logistics efficiency and reducing operational costs, crowdsourced urban logistics has attracted considerable attention from both academia [1], [4], [5] and industry (e.g., Cainiao [6], JD [7], and Amazon [8]). 
![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/6119b6e2568bd299d123cf36b03f8bf86bcf56fcc8e1a01fe3bc7889f4ddc5e8.jpg)


Fig. 1: A toy example of cross-aware parcel assignment.

A central challenge in crowdsourced urban logistics is online parcel assignment, which seeks to optimize the matching of couriers with parcels. In the literature, most existing studies focus on optimizing parcel assignment within a single platform [1], [9]. However, recent statistics [1] indicate that $6 7 . 6 \%$ of respondents demand timely delivery (e.g., within 30 minutes) of their parcels (e.g., fresh goods), highlighting the limitations of uneven spatiotemporal distribution of parcels and couriers in a single platform, particularly during peak hours, which reduces the overall quality of urban logistics services [10], [11], [12], [13]. In a city, there are typically multiple logistics platforms, each establishing service regions across the city and offering similar logistics services. Consequently, cooperative urban logistics, where couriers from other platforms (called cross-platform couriers, or cross couriers in short) are aggregated to complete parcel services for the local platform, significantly enhances the efficiency of crowdsourced FLML services. When the local platform faces a shortage of couriers to serve parcels, couriers from other platforms may be available. This approach is inspired by an emerging cooperative business model, illustrated by the following toy example. 
Example 1: As illustrated in Fig. 1(a), consider a scenario with two local-platform couriers, c1, $c _ { 2 }$ , three local-platform parcels τ1, τ2, τ3, and a cross-platform courier $c _ { 3 }$ , where each parcel can only be matched with couriers in the search range (depicted as dashed circles). There are two matching strategies: (1) Single-platform parcel assignment, where couriers are restricted to handling parcels within their own platform. As shown in Fig. 1(a), the optimal local-platform matching plan 
1 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
is $M _ { 1 } = \{ ( c _ { 1 } , \tau _ { 1 } ) , ( c _ { 2 } , \tau _ { 2 } ) \}$ . (2) Cross-platform parcel assignment, where parcels can also be assigned to couriers from cooperating platforms. The optimal cross-aware matching plan, as depicted in Fig. 1(b), is $M _ { 2 } = \{ ( c _ { 1 } , \tau _ { 1 } ) , ( c _ { 2 } , \tau _ { 2 } ) , ( c _ { 3 } , \tau _ { 3 } ) \}$ . Obviously, cross-platform parcel assignment can complete more parcels as more couriers are involved. 
Drawing on the above, leveraging available couriers from other platforms in a cooperative manner can effectively address the challenge of uneven parcel and courier distribution within the local platform [14], [15], [16], [17], [18], [19]. To this end, Li et al. [12] proposed a new task assignment model, the Global Task Assignment problem (GTA), which builds an alliance consisting of multiple platforms. The relationship among platforms thus has changed from competition to cooperation. They then designed an auction-based incentive mechanism to incentivize cooperating platforms to perform cross-platform tasks and developed a prediction-based algorithm, i.e., ImpGTA, that considers the temporal and spatial distribution over time. Obviously, GTA can improve the profit of all the platforms from a global perspective. However, it still faces the following limitations: First, [12] focuses solely on the competition and cooperation among platforms. In cross-platform settings, however, it is equally important to incentivize couriers. Since they often have heterogeneous preferences, e.g., trade-offs between detour cost and service quality. Second, task assignment operates in highly dynamic environments and requires adaptive decision ability with longterm optimization. The ImpGTA method in [12], based on prediction-window threshold rules, is essentially heuristic and lacks adaptability to real-time dynamics. To address these limitations, we investigate the Cross-Platform Urban Logistics (CPUL) problem, which explicitly models both platformlevel cooperation and courier-level incentives by enabling the local platform to dynamically leverage cross-platform couriers. Moreover, CPUL incorporates adaptive decision-making to optimize long-term revenue in highly dynamic environments. However, addressing the CPUL problem is non-trivial and involves two key challenges: (1) Since couriers are affiliated with different and self-interested cooperating platforms, the first challenge is how to design effective incentive mechanisms to encourage active participation of cross-platforms and their couriers in local parcel assignment. (2) Parcel assignment is a dynamic, large-scale combinatorial optimization problem. Thus, the second challenge is how to efficiently and adaptively determine optimal parcel assignments within the local platform under parcel and courier constraints. 
To address these challenges, we propose a Cross-Aware Parcel Assignment (CAPA) framework, which effectively and efficiently resolves the CPUL problem. First, since auction mechanisms are widely adopted for ensuring fair transactions and protecting bidder interests, we develop the Dual-Layer Auction Model (DLAM) to tackle the first challenge. Specifically, for a given cross-platform parcel, DLAM employs the First-Price Sealed Auction (FPSA) among cross-platform couriers to select the optimal courier for each cooperating platform. It then leverages the Reverse Vickrey Auction (RVA) among cooperating platforms to identify the optimal bidder. The winning courier of a cooperating platform is tasked with 
completing the assigned parcel. Second, the size of the parcel matching batch (also referred to as the time window) and the decision to assign a parcel to cooperating platforms can significantly impact the quality of parcel assignment. To deal with the second challenge, we propose a dual-stage adaptive parcel assignment method, named Reinforcement Learning Cross-Aware Parcel Assignment (RL-CAPA in short), which adaptively determines the optimal batch size and whether parcels should be assigned to cross platforms. Our main contributions are summarized as follows: 
• We formally define the novel CPUL problem that assigns parcels to optimal couriers to maximize the overall revenue of the local platform. We also prove the computational hardness of the CPUL problem. 
• We develop a cross-aware DLAM model, integrating a fair bidding mechanism for cooperating platforms and cross-couriers. We theoretically demonstrate that the DLAM auction model implemented by our proposed algorithms ensures truthfulness, individual rationality, profitability, and computational efficiency. 
• We propose the CAPA framework to address the CPUL problem, which combines an effective heuristic method and an adaptive method to optimize parcel assignment quality. 
• Extensive experiments on two datasets validate the effectiveness and efficiency of our proposed methods. 
The rest of the paper is organized as follows: Section II introduces the CPUL problem. Section III presents the proposed framework. Section IV discusses the experiments and results. Section V reviews the related work. Section VI concludes and outlines our future work. 

TABLE I: Notation and Description

<table><tr><td>Notations</td><td>Description</td></tr><tr><td>P∈P</td><td>a set of cooperating platforms</td></tr><tr><td>Loc</td><td>the local platform</td></tr><tr><td>h∈H</td><td>a set of logistics stations</td></tr><tr><td>ψ∈Ψ</td><td>a set of drop-off parcels</td></tr><tr><td>τ∈Γ</td><td>a set of pick-up parcels</td></tr><tr><td>c∈C</td><td>a set of couriers</td></tr><tr><td>d(li,lj)</td><td>the shortest path distance</td></tr><tr><td>M</td><td>a matching plan</td></tr><tr><td>Lc</td><td>the schedule of a courier c</td></tr><tr><td>p′(τ,cpwin)</td><td>the payment of P&#x27;s winner CPwin</td></tr><tr><td>p′(τ,Pwin)</td><td>the payment of the winner Pwin</td></tr><tr><td>γ</td><td>the sharing rate of P</td></tr><tr><td>μ1,μ2</td><td>the sharing rate of Loc</td></tr><tr><td>ζ</td><td>a parameter of fixed fare</td></tr><tr><td>Th</td><td>a dynamic threshold of matching</td></tr><tr><td>ω</td><td>an adjustment factor of Th</td></tr><tr><td>BF(c,τ)</td><td>the bidding function in FPAS</td></tr><tr><td>BR(P,τ)</td><td>the bidding function in RVA</td></tr></table>
# II. PROBLEM FORMULATION
In this section, we first present the system model and the auction model, followed by the definitions of relevant preliminaries. Finally, we formulate the CPUL problem. The main notations used in this paper are summarized in Table I. 
2 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/ad6563405324c2de6b8a09334f726103ca458b7f62c6b4f383c057778870b2fa.jpg)


Fig. 2: The pipeline of the system model.

# A. System Model
In our system model, couriers are responsible for completing a certain number of daily drop-off parcels while also collecting real-time pick-up requests [20], [1], [21]. There are two types of platforms in the system, i.e., the local platform Loc and a set of cooperating platforms $\mathcal { P } = \{ P _ { 1 } , \cdots , P _ { k } \}$ . It performs parcel assignment in two steps: local-platform assignment and cross-platform assignment. The pipeline of the system model is depicted in Fig. 2: $\textcircled{1}$ given a set of arriving pick-up parcels, $\textcircled{2}$ the local platform first checks for available couriers and assigns parcels to the most suitable ones. $\textcircled{3}$ If there is no available courier, the local platform broadcasts the parcel information to cooperating platforms and selects the most appropriate cross-platform courier via the proposed auction model (will be detailed in Section II-B). 
We model our system on a road network, represented by the undirected graph $\mathcal { G } _ { n } = ( V _ { n } , E _ { n } )$ , where $V _ { n }$ and $E _ { n }$ are a set of locations and roads, respectively. Each road $e _ { i j } \in E _ { n }$ connects two locations, $l _ { i }$ and $l _ { j }$ $( l _ { i } , l _ { j } \in V _ { n } )$ , and the weight of $e _ { i j }$ corresponds to the shortest path distance $d ( l _ { i } , l _ { j } )$ between $l _ { i }$ and $l _ { j }$ . In addition, we establish a network of logistics stations for each platform (including the local platform and cooperating platforms), denoted as $\mathcal { H }$ , to provide the crowdsourced FLML service across the city. Each station $h \in { \mathcal { H } }$ is represented as a triple $\boldsymbol { h } = \left( l _ { h } , C _ { h } , \mathcal { R } _ { h } \right)$ , where $l _ { h }$ is the location of $h$ $C _ { h }$ is a set of couriers managed by the station, and $\mathcal { R } _ { h }$ is the service area. In what follows, we give the definitions of drop-off parcel, pick-up parcel, and courier. 
Definition 1 (Drop-off parcel): A drop-off parcel $\psi \in \Psi$ denoted as a triple $\boldsymbol { \psi } = ( l _ { \psi } , t _ { \psi } , w _ { \psi } )$ , requires capacity $w _ { \psi }$ and should be delivered at drop-off location $l _ { \psi }$ before deadline $t _ { \psi }$ 
Definition 2 (Pick-up parcel): A pick-up parcel $\tau \in \Gamma$ is represented as a quadruple $\tau = ( l _ { \tau } , t _ { \tau } , w _ { \tau } , p _ { \tau } )$ , where $w _ { \tau }$ is the required capacity and $p _ { \tau }$ is the fare, $l _ { \tau }$ is the pick-up location and $t _ { \tau }$ is the pick-up deadline. 
Following existing studies [1], [22], we assume that the processing time for each parcel, $\tau$ or $\psi$ , is negligible, i.e., once the courier reaches the location $l _ { \tau }$ or $l _ { \psi }$ , the parcel $\tau$ or $\psi$ is considered to be completed. Besides, the parcel required capacity ( $\dot { w } _ { \tau }$ or $w _ { \psi }$ ) represents the actual volume or weight of the parcel. Since both dimensions are easily convertible, we treat them interchangeably and consistently use weight as the measure. It is important to note that in our system model, couriers get basic salaries by completing a certain number of daily drop-off parcels and earn additional bonuses for collecting pick-up parcels. Since the goal of the CPUL problem is to maximize the local platform’s overall revenue, 
we focus on finding the best task assignment between pick-up parcels and couriers in this paper. Although drop-off parcels are not directly involved in the optimization objective, they impose background constraints, such as deadline and capacity consumption, which implicitly affect couriers’ schedules. We hence follow [1], [3], [2], [9] that provide the definition of the drop-off parcels to preserve the completeness of the problem formulation and reflect real-world logistics operations. 
Definition 3 (Courier): A courier $c \in C$ is represented as a six-entry tuple $c = ( l _ { c } , w _ { c } , t _ { c } , h _ { c } , \Psi _ { c } , \Gamma _ { c } )$ , where $l _ { c }$ is the current location, $w _ { c }$ is the maximum capacity, $t _ { c }$ is the deadline to return to the attached station $h _ { c }$ , $\Psi _ { c }$ and $\Gamma _ { c }$ are a set of assigned drop-off and pick-up parcels, respectively. 
There are two types of couriers who complete the pickup parcels of the local platform: inner couriers, who belong to the local platform; and cross-platform (cross in short) couriers, who are managed by cooperating platforms. We explain that $w _ { c }$ is the maximum capacity that courier $c$ could hold parcels simultaneously in his/her delivery box. Given a courier with a set of assigned pick-up parcels $\Gamma _ { c }$ and a set of drop-off parcels $\Psi _ { c }$ , his/her schedule $L _ { c } = ( l _ { 1 } , \cdots , l _ { k } )$ is represented as a time-based sequence of locations, where $l _ { k }$ denotes the location of either a pick-up parcel or a drop-off parcel. A valid schedule $L _ { c }$ should satisfy the following constraints: 
• Capacity constraint: The total weight of parcels in $\Psi _ { c }$ and $\Gamma _ { c }$ must always satisfy $\begin{array} { r } { \sum _ { \psi \in \Psi _ { c } } w _ { \psi } + \sum _ { \tau \in \Gamma _ { c } } w _ { \tau } \leq w _ { c } } \end{array}$ i.e., the courier’s delivery box capacity $w _ { c }$ . 
• Deadline constraint: The assigned courier $c$ must arrive at $l _ { \tau }$ and $l _ { \psi }$ $\tau \in \Gamma _ { c }$ and $\psi \in \Psi _ { c , \mathrm { ~ \tiny ~ \textnormal ~ { ~  ~ } ~ } }$ before both parcel deadline (i.e., $t _ { \tau }$ and $t _ { \psi }$ ) and courier deadline $t _ { c }$ . 
• Invariable constraint: One parcel only needs a courier to complete, and once parcels in $\Psi _ { c }$ and $\Gamma _ { c }$ are assigned to the courier $c$ , they cannot be changed. 
Following the existing works [23], [1], [9], we insert the new location of pick-up parcel $\tau$ into the optimal position in $L _ { c }$ by minimizing the total travel distance, without causing any reordering. As discussed in [1], [24], reordering all scheduled locations significantly increases computational overhead, making it unsuitable for real-time scenarios where parcel insertion operations are invoked frequently. 
# B. Auction Model
The auction model is a typical incentive mechanism that motivates participants to actively and truthfully compete for items [1], [12], [25], [26], [27]. Traditional auction models primarily rely on a single-layer auction [1], [12] to find the best courier for each parcel. However, in our system model, the local platform cooperates with other platforms to improve the quality of parcel assignment. To this end, exploring how to bid among platforms and their couriers is a key issue. Hence, we introduce our auction model, i.e., DLAM, which aims to find the best assignments between parcels and cross couriers through a double-layer auction process: 
• In the first layer, the DLAM employs a First-Price Sealed Auction (FPSA) among cross-platform couriers, where bidders are cross-platform couriers and the highest bidder wins the assignment. 
3 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
• In the second layer, the DLAM leverages the Reverse Vickrey Auction (RVA) among cooperating platforms, where bidders are cooperating platforms, and the lowest bidder wins but pays the second-lowest bid price. 
Compared to single-layer auction models [1], [12], DLAM considers the true bids of cooperating platforms and their couriers, ensuring the revenues of all three involved parties, i.e., the platform, cooperating platforms, and couriers. In what follows, we detail the FPSA and RVA. 
In the FPSA, to avoid cross couriers maliciously bid, we calculate the courier’s bid based on the courier’s preference for pick-up parcels, in which the platform could control the upper bound of the bidding price. Specifically, given a cooperating platform $P$ , each belonged courier $c _ { P } ^ { i }$ determines his/her optimal bid $B _ { F } ( c _ { P } ^ { i } , \tau )$ in terms of detour ratio $\Delta d _ { \tau }$ , and performance quality $g ( c _ { P } ^ { i } )$ in historical parcel services, which is calculated as follows: 
$$
B _ {F} (c _ {P} ^ {i}, \tau) = p _ {\mathrm {m i n}} + \left(\alpha_ {c _ {P} ^ {i}} \cdot \Delta d _ {\tau} + \beta_ {c _ {P} ^ {i}} \cdot g (c _ {P} ^ {i})\right) \gamma p _ {\tau} ^ {\prime}, \quad (1)
$$
where $\gamma$ denotes the sharing rate of $P$ , $p _ { \mathrm { m i n } }$ is the basic price satisfying $p _ { m i n } \leq ( 1 - \gamma ) p _ { \tau } ^ { \prime } , \alpha _ { c }$ i and $\beta _ { c _ { P } ^ { i } }$ are two preference coefficients to balance the effect of $\Delta d _ { \tau }$ and $g ( c _ { P } ^ { i } )$ , and $p _ { \tau } ^ { \prime }$ is the maximum payment that $P$ is willing to offer its couriers with respect to $\tau$ . For simplicity, we set $p _ { \tau } ^ { \prime } = \mu _ { 1 } p _ { \tau }$ , where $\mu _ { 1 }$ is the sharing rate of Loc. The detour ratio is calculated $\begin{array} { r } { \Delta d _ { \tau } = \operatorname* { m i n } _ { 1 < k \leq | L _ { c } | - 1 } 1 - \frac { d ( l _ { k } , l _ { k + 1 } ) } { d ( l _ { k } , l _ { \tau } ) + d ( l _ { \tau } , l _ { k + 1 } ) } } \end{array}$ $g ( c _ { P } ^ { i } )$ $\begin{array} { r } { g ( c _ { P } ^ { i } ) = \frac { 1 } { 3 N } \sum _ { j = 1 } ^ { N } ( Q S _ { c _ { P } ^ { i } } ^ { j } + E S _ { c _ { P } ^ { i } } ^ { j } + C S _ { c _ { P } ^ { i } } ^ { j } ) } \end{array}$ 13N PNj=1(QSjci P c iP where $N$ Pindicates the total number of historical delivery parcels, $Q S _ { c _ { P } ^ { i } } ^ { j }$ is quality score, $E S _ { c _ { P } ^ { i } } ^ { j }$ is efficiency score, and c iP c iP $C S _ { c _ { P } ^ { i } } ^ { j }$ c is customer satisfaction score. These three values of attributes are evaluated by historical data and mapped to a range of 0-1. It is important to note that each courier $c _ { P } ^ { i }$ bids based on their independent evaluation of the parcel, without knowledge of the bids from other bidders. To this end, the cooperating platforms could control the payment through $p _ { m i n }$ and $\gamma$ to ensure their revenue. As can be seen from the bidding price model above, couriers with shorter detours (i.e., the service cost is minimum) and better historical performance can provide higher quality service. In this way, the cooperating platform $P$ selects the highest-bid courier $c _ { P } ^ { i }$ as the winner, and his/her bid is considered to be the winning price, i.e., 
$$
p ^ {\prime} (\tau , c _ {w i n} ^ {P}) = \max  \left\{B _ {F} \left(c _ {P} ^ {i}, \tau\right) \mid c _ {P} ^ {i} \in C _ {P} \right\}. \tag {2}
$$
In the RVA, each cooperating platform $P$ uses the highest bid $p ^ { \prime } ( \tau , c _ { w i n } ^ { P } )$ in the first-layer auction as the starting price of the second-layer auction. Given a pick-up parcel $\tau$ , and $k$ candidate cooperating platforms $\mathcal { P } _ { \tau } = \{ P _ { 1 } , \cdots , P _ { k } \}$ , the bid for each cooperating platform $P \in \mathcal { P } _ { \tau }$ is determined by considering two key factors: the starting bid $p ^ { \prime } ( \tau , c _ { w i n } ^ { P } )$ , and the cooperation quality $f ( P )$ with the local platform Loc. Based on these considerations, the bidding function $B _ { R } ( P , \tau )$ is defined as follows, 
$$
B _ {R} (P, \tau) = \left\{ \begin{array}{l l} p ^ {\prime} (\tau , c _ {w i n} ^ {P}) + \mu_ {2} p _ {\tau} & \text {i f} | \mathcal {P} _ {\tau} | = 1 \\ p ^ {\prime} (\tau , c _ {w i n} ^ {P}) + f (P) \mu_ {2} p _ {\tau} & \text {i f} | \mathcal {P} _ {\tau} | \geq 2 \end{array} \right., \tag {3}
$$
where $\mu _ { 2 }$ is a sharing rate of Loc satisfying $\mu _ { 1 } + \mu _ { 2 } \leq 1$ , and cooperation quality satisfies $f ( P ) \leq 1$ . As for Eq. 3, when 
there is a single bidder, i.e., $| \mathcal { P } _ { \tau } | = 1$ , the payment reaches the maximum value. For the common case where $| \mathcal { P } _ { \tau } | \geq 2$ , the bid $B _ { R } ( P , \tau )$ of $P$ is guaranteed by $p ^ { \prime } ( \tau , c _ { w i n } ^ { P } )$ , and could obtain an additional reward by considering cooperation quality $\begin{array} { r } { f ( P ) = \frac { \overline { Q } _ { P } ^ { L o c } } { T _ { L o c } } } \end{array}$ TLoc , where $\overline { { Q } } _ { P } ^ { L o c }$ QP represents the average historical cooperation quality between $P$ and Loc calculated by the average performance $g ( c _ { P } ^ { i } )$ of all cross couriers, and $T _ { L o c }$ denotes the historical maximum cooperation quality between all cooperating platforms and the local platform. It is worth noting that the current formulation of preference modeling is not restricted to these following attributes and can be easily extended to incorporate additional factors. For example, one possible extension is that we can replace $\alpha _ { c _ { P } ^ { i } } { \cdot } \Delta d _ { \tau } { + } \beta _ { c _ { P } ^ { i } } { \cdot } g ( c _ { P } ^ { i } )$ or $f ( P )$ with $\vec { \omega } \cdot \vec { \Delta }$ , where $\vec { \omega } = ( \omega _ { 1 } , \cdot \cdot \cdot , \omega _ { m } )$ represents the effect coefficients, and $\vec { \Delta } = ( \Delta _ { 1 } , \cdots , \Delta _ { m } )$ denotes a vector of different preference attributes. In RVA, the cooperating platform $P$ with the lowest bid is selected as the winner $P _ { w i n }$ , and the second-lowest bid among all bids $p _ { \tau } ^ { \prime } ( \tau , P _ { w i n } )$ is considered as the final payment to $P _ { w i n }$ , i.e., 
$$
p ^ {\prime} (\tau , P _ {w i n}) = \min  \left\{B _ {R} (P, \tau) | P \in \left(\mathcal {P} \backslash P _ {w i n}\right) \right\}. \tag {4}
$$
We clarify that $p ^ { \prime } ( \tau , c _ { w i n } ^ { P } )$ is the payment to the winner courier c w in $c _ { w i n } ^ { P }$ in the first-layer auction, and $p ^ { \prime } ( \tau , P _ { w i n } )$ is the payment to the winner cooperating platform $P _ { w i n }$ in the second-layer auction. Moreover, to enhance clarity, we use $p ^ { \prime } ( \tau , c ^ { P _ { w i n } } )$ to represent the final payment for the parcelcourier assignment, which corresponds to $p ^ { \prime } ( \tau , P _ { w i n } )$ . Note that the double-layer auctions discussed in this paper are conducted under sealed-bid conditions, which means that couriers and platforms only need to provide their own preference attributes without knowledge of the bids submitted by others [28], [26], [29]. To further exemplify the operation of DLMA, we give a toy example as follows. 
Example 2: Suppose that there are a pick-up parcel $\tau$ of the local platform Loc with a fare $p _ { \tau }$ and two cooperative platforms $P _ { 1 } , P _ { 2 }$ . In the FPSA, the workers in the two independent platforms auction with the highest sealed policy. Assuming that winner bidding prices are $B _ { F } ( c _ { P _ { 1 } } ^ { i } , \tau ) = 2 . 5$ and $B _ { F } ( c _ { P _ { 2 } } ^ { j } , \tau ) = 3 . 5$ respectively. Next, based on $B _ { F } ( c _ { P _ { 1 } } ^ { i } , \tau )$ and $B _ { F } ( c _ { P _ { 2 } } ^ { j ^ { - } } , \tau )$ , in the RVA, $P _ { 1 }$ and $P _ { 2 }$ give bids of $B _ { R } ( P _ { 1 } , \tau ) =$ 2.8 and $B _ { R } ( P _ { 2 } , \tau ) = 3 . 7$ , respectively. According to the policy of RVA, the cross-platform winner is $P _ { 1 }$ with the payment 3.7. 
# C. Problem Formulation
Based on the system and auction models above, in this section, we formally introduce the revenue of the local platform and the definition of the CPUL problem. 
Definition 4 (Revenue): Given a pick-up parcel $\tau$ , when the parcel $\tau$ is completed by an inner courier $c _ { i }$ , the revenue of the local platform is $p _ { \tau } - R c ( \tau , c _ { i } )$ , where $R c ( \cdot , \cdot )$ denotes the payment for $c _ { i }$ ; when $\tau$ is performed by a courier $c _ { j }$ from cooperating platform $P$ , the revenue of the local platform is $p _ { \tau } - p ^ { \prime } ( \tau , c _ { j } )$ , where $p ^ { \prime }$ denotes the payment for $P$ . 
Simply put, we calculate $R c ( \tau , c )$ of the matching pair $( \tau , c )$ with a fixed fare $R c ( \tau , c ) ~ = ~ \zeta \cdot p _ { \tau }$ , where $\zeta$ is an adjustable parameter. To concentrate on the proposed auction mode, we simplify that the local platform does not participate 
4 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/78eca944756169c73d5cb17f25df5b917de9ab7b3c5e318956aaa96d0f71bd80.jpg)


Fig. 3: The pipeline of the CAPA framework.

in the cross-platform parcel assignments of other platforms. Accordingly, the platform’s revenue is primarily derived from the successful completion of inner pick-up parcels. In addation, since tasks arrive at the platform continuously as a stream, we adopt a widely used strategy in [1], [30], [2] by partitioning the task stream into batches (i.e., time windows) and conducting task assignment at the end of each batch. Although the batch-based strategy may be less efficient than instant matching [31], [9], previous works [9], [24], [30] have shown that it is worthwhile to exchange a slight delay for an improved matching quality. To this end, we formally define the CPUL problem. 
Definition 5 (CPUL Problem): Given a set of pick-up parcels $\Gamma _ { L }$ , a set of inner couriers $C _ { L }$ and a set of cooperative platforms $\mathcal { P }$ with cross couriers $C _ { \mathcal { P } }$ , the CPUL problem aims to find the best parcel assignment that maximizes the overall revenue of the local platform, which is formulated as 
$$
\begin{array}{l} R e v _ {S} \left(\Gamma_ {L}, C _ {L}, \mathcal {P}\right) = \sum_ {\left(\tau_ {i}, c _ {i}\right) \in \Gamma_ {L} \times C _ {L}} \left(p _ {\tau_ {i}} - R c \left(\tau_ {i}, c _ {i}\right)\right) \\ + \sum_ {\left(\tau_ {j}, c _ {j}\right) \in \Gamma_ {L} \times C _ {\mathcal {P}}} \left(p _ {\tau_ {j}} - p _ {\tau_ {j}} ^ {\prime} \left(\tau_ {j}, c _ {j}\right)\right). \end{array} \tag {5}
$$
In what follows, we theoretically analyze the hardness of the CPUL problem in Theorem 1. 
Theorem 1: The CPUL problem is NP-hard. 
Proof: Due to space limitations, the proof is shown in Appendix A.1. □ 
# III. PROPOSED SOLUTION
In this section, we introduce the CAPA framework to address the CPUL problem and detail its main components. 
# A. Framework Overview
As illustrated in Fig. 3, the CAPA framework optimizes parcel assignment by integrating local-platform and crossplatform collaboration. Specifically, as presented in Algorithm 1, given a stream of pick-up parcels $\Gamma$ and a set of couriers 

Algorithm 1: Cross-Aware Parcel Assignment (CAPA)

Input: a stream of pick-up parcels $\Gamma$ and a set of couriers $C$ in Loc, a set of cooperating platforms $\mathcal{P}$ and a batch size $\Delta b$ Output: a matching plan $\mathcal{M}$ 1 $\mathcal{M} \gets \emptyset$ , $\Gamma_S \gets \emptyset$ and $t_{cum} = 0$ ;  
2 while timeline $t$ is not terminal do  
3 Retrieve arriving pick-up parcels $\Gamma_t$ at $t$ from $\Gamma$ ;  
4 $\Gamma_S \gets \Gamma_S \cup \Gamma_t$ ;  
5 if $t_{cum} == \Delta b$ then  
6 Retrieve available inner couriers $C_S$ from $C$ ; Retrieve available platforms $\mathcal{P}_S$ from $\mathcal{P}$ ;  
7 $\mathcal{M}_{lo}, \mathcal{L}_{cr} \gets$ call CAMA Algorithm $(\Gamma_S, C_S)$ ;  
8 $\mathcal{M}_{cr} \gets$ call DAPA Algorithm $(\mathcal{P}_S, \mathcal{L}_{cr})$ ;  
9 $\mathcal{M} \gets \mathcal{M} \cup \mathcal{M}_{lo} \cup \mathcal{M}_{cr}$ ;  
10 $\mathcal{M}_{cr} \gets \emptyset$ , $\mathcal{M}_{lo} \gets \emptyset$ , $\Gamma_t \gets \emptyset$ and $t_{cum} = 0$ ;  
11 $t_{cum} = t_{cum} + 1$ ;  
12 return $\mathcal{M}$ 
$C$ in the local platform Loc, a set of cooperating platforms $\mathcal { P }$ and a batch size threshold $\Delta b$ , the local platform first perceives the real-time environment to obtain the dynamic status and distribution of parcels and couriers, and accumulates the parcel stream into sequential batches (lines 1-4). In each batch, parcels with matching utility values $u ( \tau , c )$ exceeding the dynamic threshold $T _ { h }$ are directly assigned to the corresponding couriers by the CAMA algorithm (line 6). Otherwise, parcels enter an auction pool to perform cross-platform parcel assignment (line 7). Finally we summarize the matching plan derived from the CAMA and the CAPA (line 8). Specifically, for each parcel in the auction pool, the CAPA processes parcels as follows: $\textcircled{1}$ Couriers eligible for cross-platform assignment receive information about the parcels in the auction pool. $\textcircled{2}$ In each cross platform, couriers place bids according to FPSA algorithm, and then the optimal courier is pre-allocated. $\textcircled{3}$ The bidding between cross platforms is further conducted using 
5 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
the RVA algorithm. $\textcircled{4}$ The local platform confirms the final winner. $\textcircled{5}$ The local platform notifies the respective platform and its winning courier to complete the pick-up parcel. 
The CAPA framework integrates local-platform assignment and cross-platform assignment, ensuring parcel matching efficiency, and achieving a win-win situation for all parties involved. In what follows, we detail all involved algorithms. 
# B. Local-Platform Parcel Assignment
In the local-platform parcel assignment phase, we propose the CAMA algorithm to efficiently identify the optimal inner courier for each pick-up parcel in a batch manner. As illustrated in the yellow area of Fig. 3, CAMA initially adopts a quality-aware strategy to assign each parcel to a suitable courier, with the objective of maximizing the local platform’s revenue. More specifically, a dynamic threshold is applied to categorize parcels as either high-quality or low-quality. Highquality parcels are directly matched with the optimal local couriers, while low-quality parcels are deferred to the auction pool for potential cross-platform assignment. The parcels that are not allocated in the current batch (i.e., neither matching in the current local-platform assignment nor cross-platform assignment) will reenter the next batch for re-matching. 
To evaluate the quality of a potential matching pair $( \tau , c )$ between a parcel $\tau$ and an inner courier $c$ , we introduce a utilityaware evaluator $u ( \tau , c )$ that jointly considers the parcel’s required capacity and detour distance incurred by the courier. Intuitively, the local platform prioritizes assigning parcels to couriers with greater remaining capacity and minimal detour distance. As such, the utility $u ( \tau , c )$ is computed as follows: 
$$
u (\tau , c) = \phi \cdot \Delta w _ {\tau} + (1 - \phi) \cdot \Delta d _ {\tau}, \tag {6}
$$
where $\begin{array} { r } { \Delta w _ { \tau } \ = \ 1 - \ \frac { \sum _ { \psi \in \Psi _ { c } } w _ { \psi } + \sum _ { \tau \in \Gamma _ { c } } w _ { \tau } } { w _ { c } } } \end{array}$ is the unoccupied capacity ratio, ∆dτ = min1≤i≤|Sw|−1 i i+1 d(li,lτ )+d(lτ ,li+1) $\begin{array} { r } { \Delta d _ { \tau } ~ = ~ \operatorname* { m i n } _ { 1 \leq i \leq | S _ { w } | - 1 } \frac { d ( l _ { i } , l _ { i + 1 } ) } { d ( l _ { i } , l _ { \tau } ) + d ( l _ { \tau } , l _ { i + 1 } ) } } \end{array}$ is the detour-related ratio, and $\phi$ is a balance coefficient. To distinguish high-quality parcels, we also maintain a dynamic threshold $T _ { h }$ , which is adaptively updated based on the average utility of all potential matching pairs $M _ { t }$ , i.e., 
$$
T _ {h} = \omega \cdot \frac {\sum_ {k = 1} ^ {t} \sum_ {(\tau_ {i} , c _ {j}) \in \mathcal {G} _ {k}} ^ {t} u (\tau_ {i} , c _ {j})}{\sum_ {k = 1} ^ {t} | \mathcal {G} _ {k} |}, \tag {7}
$$
where $\omega$ is a sensitivity adjustment factor and $M _ { t }$ records all potential matching pairs. 
Algorithm details. Algorithm 2 presents the pseudo-code of the CAMA algorithm, which is designed to efficiently assign pick-up parcels within the local platform Loc. Given a batch of pick-up parcels $\Gamma _ { t }$ and a set of local couriers $C _ { S }$ , CAMA first identifies all feasible courier-parcel pairs by verifying constraints such as arrival time and capacity (Lines 2–7). For each parcel with at least one feasible courier, the algorithm selects the courier yielding the highest utility and adds the corresponding pair to a candidate set $\mathcal { G }$ (Lines 8–11). If no feasible courier is found, the parcel is directly added to the auction pool $\mathcal { L } _ { c r }$ for potential cross-platform assignment(Line 13). Subsequently, a dynamic utility threshold $T _ { h }$ is computed based on the average utility of all candidate pairs (Line 14). Based on this threshold, the algorithm assigns high-utility pairs 

Algorithm 2: Cross-aware Matching Algorithm (CAMA)

Input: parcels $\Gamma_{t}$ , couriers $C S$ Output: a matching plan $\mathcal{M}_{lo}$ and an auction pool $\mathcal{L}_{cr}$ 1 $\mathcal{G}_t\gets \emptyset$ $\mathcal{L}_{cr}\gets \emptyset$ $\mathcal{M}_t\gets \emptyset$ .   
2 for each parcel $\tau_{i}\in \Gamma_{t}$ do   
3 $\mathcal{S}_{\tau_i}\gets \emptyset$ .   
4 for each courier $c_{j}\in C_{S}$ do   
5 if the matching of $c_{j}$ and $\tau$ is valid then   
6 Compute matching utility $u(\tau_i,c_j)$ .   
7 Add $(\tau_{i},c_{j},u(\tau_{i},c_{j}))$ into $\mathcal{S}_{\tau_i}$ .   
8 if $\mathcal{S}_{\tau_i}\neq \emptyset$ then   
9 $\mathcal{G}_t\gets \mathcal{G}_t\cup \mathcal{S}_{\tau_i};$ 10 else   
11 $\mathcal{L}_{cr}\leftarrow \mathcal{L}_{cr}\cup \{\tau_i\} ;$ 12 Update threshold $T_{h}$ via Eq. 7 based on $\mathcal{G}_t$ .   
13 for each parcel $\tau_{i}\in \Gamma_{t}$ do   
14 flag FALSE;   
15 for each $(\tau_{i},c_{j},u(\tau_{i},c_{j}))\in \mathcal{G}_{t}$ do   
16 if $u(\tau_i,c_j)\geq Th$ then   
17 $\mathcal{M}_t\gets \mathcal{M}_t\cup \{(\tau_i,c_j)\} ;$ 18 flag $\leftarrow$ TRUE;   
19 if flag $=$ FALSE then   
20 $\mathcal{L}_{cr}\leftarrow \mathcal{L}_{cr}\cup \{\tau_i\} ;$ 21 Compute $\mathcal{M}_{lo}$ from $M_t$ using KM algorithm;   
22 return $\mathcal{M}_{lo},\mathcal{L}_{cr}$ 
(i.e., those satisfying $u ( \tau , c ) \geq T _ { h } )$ to form the local parcel assignment $\mathcal { M } _ { l o }$ , while putting the remaining parcels into the auction pool $\mathcal { L } _ { c r }$ for further processing (Lines 15–19). The algorithm outputs both the finalized local assignments $\mathcal { M } _ { l o }$ and the updated auction pool $\mathcal { L } _ { c r }$ (Line 20). 
Complexity Analysis. The time complexity of the CAMA algorithm is $O ( n m )$ , where n, m represent the number of parcels and inner couriers, respectively. 
# C. Cross-Platform Parcel Assignment
When local-platform parcels cannot be effectively served by inner couriers, as depicted in the green area of Fig. 3, they are collected to an auction pool $\mathcal { L } _ { c r }$ for cross-platform assignment, and further processed by the DAPA algorithm. The DAPA algorithm operates through two hierarchical auction layers. In the first layer, each participating platform conducts FPSA internally, allowing its couriers to bid competitively for cross parcels. In the second layer, RVA is employed across cooperating platforms to determine the winning platform based on the most cost-effective bids. 
In the DAPA algorithm, parcel information in the auction pool, such as weight and location, is initially broadcast to all cooperating platforms, which in turn repeat it to their affiliated couriers. In the first-layer FPSA, each cooperating platform independently conducts internal auctions among its couriers. Couriers evaluate the bids for parcels based on their current status and submit sealed bids $B _ { F } ( c _ { P } ^ { i } , \tau )$ for desirable parcels. The courier with the highest bid wins the parcel, and the winning bid becomes the final transaction price. The winning couriers from each platform are then passed to the second-
6 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/ce0bf7d23ab88d7c92ee4bbfe12cd9379732e13a966ec3e46a85760e621cdae9.jpg)


Fig. 4: A toy example of the DAPA algorithm.

layer inter-platform auction for cross-platform selection. We give a running example to illustrate the operation of FPSA. 
Example 3: As illustrated in pipeline $\textcircled{1}$ of Fig. 4, consider a parcel with a weight of 0.8 (i.e., subject to a capacity constraint) and a fare of 10. The sharing rates at the two-level auction stages are set as $\mu _ { 1 } = 0 . 5$ and $\mu _ { 2 } = 0 . 4$ . Hence, the maximum price $P _ { l i m } ( \tau )$ that the local platform Loc is willing to pay to a cooperating platform is 9.0, while the maximum fare allocated for the first-tier FPSA stage is 5.0. Assume that three couriers from platform $P _ { 1 }$ submit the following bids: $B _ { F } ( c _ { P _ { 1 } } ^ { 1 } , \tau ) = 3 . 6 2$ , $B _ { F } ( c _ { P _ { 1 } } ^ { 2 } , \tau ) = 3 . 6 6$ , and $B _ { F } ( c _ { P _ { 1 } } ^ { 3 } , \tau ) =$ 3.80. Since $B _ { F } ( c _ { P _ { 1 } } ^ { 3 } , \tau ) > \dot { B } _ { F } ( c _ { P _ { 1 } } ^ { 2 } , \tau ) > B _ { F } ( c _ { P _ { 1 } } ^ { 1 } , \tau )$ , courier $c _ { P _ { 1 } } ^ { 3 }$ is declared the winner on platform $P _ { 1 }$ . Similarly, in the internal FPSA auctions of other cooperating platforms, courier $c _ { P _ { 2 } } ^ { 3 }$ wins on platform $P _ { 2 }$ with a bid of 5.54, and courier $c _ { P _ { 3 } } ^ { 2 }$ wins on platform $P _ { 3 }$ with a bid of 3.26. 
The second-layer auction RVA is conducted among cooperating platforms to determine the selected platform based on the winning bid of FPSA. In the RVA, the platform offering the lowest bid is selected as the winner, but is paid using the second-lowest bid. The payment is executed only if it does not exceed the upper limit predefined payment $P _ { l i m } ( \tau )$ by the local platform, thereby ensuring that interplatform cooperation remains both cost-effective and mutually beneficial. 
Example 4: As illustrated in pipeline $\textcircled{2}$ of Fig. 4, the local platform selects the platform that submits the lowest bid, while the final payment is set to the second-lowest bid. The numbers in parentheses beside each cooperating platform represent their average historical collaboration quality scores. Specifically, for parcel $\tau$ , platforms $P _ { 1 }$ , $P _ { 2 }$ , and $P _ { 3 }$ submit bids of 5.59, 9.29, and 5.75, respectively. The bid ranking satisfies the order $B _ { R } ( P _ { 1 } , \tau ) < B _ { R } ( P _ { 3 } , \tau ) < P _ { \mathrm { l i m } } ( \tau ) < B _ { R } ( P _ { 2 } , \tau )$ , where the bid from $P _ { 2 }$ exceeds the upper payment limit $P _ { \mathrm { l i m } } ( \tau ) = 9 . 0$ set by the local platform. As such, $P _ { 2 }$ is disqualified, and $P _ { 1 }$ is selected as the winning platform. According to the RVA mechanism, $P _ { 1 }$ is paid the second-lowest bid, i.e., 5.75. Platform $P _ { 1 }$ then assigns the parcel to its winning courier $c _ { P _ { 1 } } ^ { 3 }$ , 

Algorithm 3: Dual-layer Auction-based Parcel Assignment (DAPA)

Input: a set of cross parcels $\mathcal{L}_{cr}$ , cross platforms $\mathcal{P}_S$ Output: a matching plan $\mathcal{M}_{cr}$ 1 $\mathcal{M}_{cr} \gets \phi$ ;  
2 for each parcel $\tau_i \in \mathcal{L}_{cr}$ do  
3 /* Step1: The FPSA process */  
4 $\mathcal{B}_{\tau_i} \gets \emptyset$ ;  
5 for each platform $P_j \in \mathcal{P}_S$ do  
6 $\mathcal{B}_F \gets \emptyset$ ;  
7 Obtain all available workers $C_{P_j}$ in $P_j$ ;  
8 if the matching $(c_{P_j}^k, \tau_i)$ is valid then  
9 invoke Eq. 1 to calculate $B_F(c_{P_j}^k, \tau_i)$ ;  
10 Add $\{(\tau_i, c_{P_j}^k, B_F(c_{P_j}^k, \tau_i))\}$ into $\mathcal{B}_F$ ;  
11 if $\mathcal{B}_F$ is not empty then  
12 Sort $\mathcal{B}_F$ in descending order of $B_F(c_{P_j}^k, \tau_i)$ ;  
13 Pop the first tuple $(\tau_i, c_{P_j}^*)$ in $\mathcal{B}_F$ ;  
14 Add $\{(\tau_i, c_{P_j}^*, P_j, B_F(c_{P_j}^k, \tau_i))\}$ into $\mathcal{B}_{\tau_i}$ ;  
15 /* Step2: The RVA process */  
if $|\mathcal{B}_{\tau_i}| \geq 2$ then  
16 $\mathcal{B}_R \gets \emptyset$ ;  
17 for each $(\tau_i, c_{P_j}^k, P_j) \in \mathcal{B}_{\tau_i}$ do  
18 invoke Eq. 3 to calculate $B_R(P_j, \tau_i)$ ;  
19 Add $\{(c_{P_j}^k, \tau_i, P_j, B_R(P_j, \tau_i))\}$ into $\mathcal{B}_R$ ;  
20 Sort $\mathcal{B}_R$ in ascending order of bids $B_R(P_j, \tau_i)$ ;  
21 Pop the first tuple $(c_{Pwin}^k, \tau_i, Pwin)$ in $\mathcal{B}_R$ ;  
22 Invoke Eq. 4 to calculate $p'(\tau_i, Pwin)$ ;  
23 $\mathcal{M}_{cr} \gets \mathcal{M}_{cr} \cup \{(\tau_i, c_{Pwin}^k)\}$ ;  
24 if $|\mathcal{B}_{\tau_i}| = 1$ then  
25 $p'(\tau_i, Pwin) = B_F(c_{Pwin}^k, \tau_i) + \mu_2 p_\tau$ ;  
26 $\mathcal{M}_{cr} \gets \mathcal{M}_{cr} \cup \{(\tau_i, c_{Pwin}^k)\}$ ;  
27 return return $\mathcal{M}_{cr}$ 
who previously bid 3.8 during the FPSA stage. As a result, the revenue of platform $P _ { 1 }$ is1.95; the revenue of the local platform Loc is 4.25. 
Algorithm details. The pseudo-code of the DAPA algorithm is presented in Algorithm 3, which allocates parcels in the auction pool to cross couriers via a dual-layer auction mechanism. For each parcel $\tau _ { i }$ , DAPA first performs FPSA in each cooperating platform (Lines 4–15). Specifically, for each cooperating platform $P _ { j }$ , it identifies all available couriers and evaluates the feasibility of assigning parcel $\tau _ { i }$ to each courier based on predefined constraints. If a match is valid, the courier submits a sealed bid $B _ { F } ( c _ { P _ { j } } ^ { k } , \tau _ { i } )$ according to Eq. 1, and all valid bids are collected into the set $\boldsymbol { B } _ { F }$ (Lines 7–11). If $\boldsymbol { B } _ { F }$ is non-empty, the courier with the highest bid is selected as the internal winner for $\tau _ { i }$ , and the bid is added to the inter-platform bid set $B _ { \tau _ { i } }$ (Lines 12–15). The DAPA then proceeds to RVA (Lines 17–28). If at least two cooperating platforms have submitted bids (i.e., $| B _ { \tau _ { i } } | \geq 2 )$ ), platform-level bids $B _ { R } ( P _ { j } , \tau _ { i } )$ are computed based on Eq. 3 and stored in $\scriptstyle { B _ { R } }$ . The platform offering the lowest bid is selected as the winner, while the final 
7 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/d2ab83a27f070f9d8d90870564649fb0da14a96e4b0e8cc9dc15f8b53976b75e.jpg)


Fig. 5: The pipeline of the RL-CAPA method.

transaction price is set to the second-lowest bid to promote truthful bidding (Lines 22–24). The resulting assignment is recorded in the matching set $\mathcal { M } _ { c r }$ (Line 25). If only one platform participates, the winner is assigned by default, and the transaction price is set to the maximum allowed value defined by Eq. 3 (Lines 27–28). After all parcels have been processed, the algorithm returns the final cross-platform courier-parcel assignment set $\mathcal { M } _ { c r }$ (Line 29). 
Complexity Analysis. The time complexity of the DAPA algorithm is $O ( n m p \log m + n p \log p )$ , where $n , ~ m$ , and $p$ are the number of parcels, couriers per platform, and cooperating platforms, respectively. The FPSA process contributes $O ( n m p \log m )$ , and the RVA process adds $O ( n p \log p )$ . 
Discussion. In the auction model DLAM, both cooperating platforms and couriers do not directly rely on human-inthe-loop bid. They predefine candidate preference coefficient combinations (e.g., $\alpha _ { P } ^ { i }$ and $\beta _ { P } ^ { i }$ in Eq. (1)). Upon parcel arrival, the system automatically selects an appropriate coefficient combination based on predefined rules or supervised agents [1], [19], and then efficiently computes the bidding values. Therefore, this process does not require human intervention for each parcel, allowing all participants to submit bids with minimal computational overhead under dynamic arrivals. In the following, we provide a theoretical analysis and formal proof that the DLAM auction model implemented by DAPA is effective, as stated in Theorem 2. 
Theorem 2: The DAPA algorithm possesses the four key attributes of the auction model: truthfulness, individual rationality, profitability, and computational efficiency. 
Proof: Due to space limitations, the proof is shown in Appendix A.2. □ 
# D. Dual-Stage Adaptive Assignment Optimization
Although the CAMA can effectively address the CPUL problem with less computational complexity, it often falls into the local optimum of parcel assignment, due to the lack of consideration of long-term rewards. Besides, realtime parcel assignment is inherently complex and dynamic, involving multiple factors such as parcel deadlines and courier capacity. Traditional methods, such as CAMA, are often limited in their ability to account for long-term rewards. In contrast, reinforcement learning (RL) offers significant advantages by dynamically adjusting decisions based on longterm rewards, adapting to changing environments, and learning 
optimal strategies over time. We hence introduce the RLbased method to address the CPUL problem. Based on the baseline CAPA framework, we observe that two limitations. First, the distribution of parcels in the time dimension is non-uniform. For example, batches during peak hours may contain excessive pick-up parcels, while idle periods see sparse arrivals. Parcel assignment within fixed time batch sizes [1], [32] or fixed numbers of percels [13] encounters challenges in adapting to dynamic adjustment of the number of parcels. Recent studies [33], [9] have theoretically proven that if the inbatch matching algorithm yields a local optimum, e.g., via the KM algorithm [34], then there exists an adaptive batch-based strategy that guarantees the overall performance. Second, each inner-platform parcel faces a binary decision: staying on the local platform or being assigned to cross platforms. Different actions bring different rewards, which also have dynamic properties and long-term effects. The dynamic threshold-based method in Algorithm 2 cannot effectively consider complex environmental states and long-term benefits. 
To this end, we propose the RL-CAPA, a dual-stage adaptive assignment method based on hierarchical policy learning. As illustrated in Fig. 5, RL-CAPA dynamically adjusts the time batch size to improve efficiency, and adaptively determines a series of cross-or-not decisions of inner parcels within each time batch, i.e., either moving to the next batch or the auction pool. These two processes are mutually influential and work in tandem to address the CPUL problem effectively. More specifically, the RL-CAPA first observes the global state $s _ { t }$ and samples a first-stage action $a _ { t } ^ { ( 1 ) }$ from policy $\pi _ { 1 } ( a _ { t } ^ { ( 1 ) } \mid s _ { t } )$ , where $a _ { t } ^ { \left( 1 \right) }$ denotes the selected batch time-window size. 
• Action Space $A _ { b }$ . The local platform is modeled as an agent that observes the environment and selects a batch size from the from the discrete action space $A _ { b } \ = \ [ h _ { L } , h _ { L + 1 } , \cdot \cdot \cdot , h _ { M } ]$ , where $h _ { L }$ and $h _ { M }$ denote the minimum and maximum allowable batch sizes, respectively. Each action $a _ { t } ^ { ( 1 ) } \in A _ { b }$ represents a specific batch duration. For example, if $h _ { L } = 1 0$ and $h _ { M } = 2 0$ , the local platform can choose any of the 11 discrete tions (i.e., represents $a _ { t } ^ { ( 1 ) } \in \{ 1 0 , 1 1 , \cdot \cdot \cdot , 2 0 \} )$ . The action-second . $a _ { t } ^ { ( 1 ) } = 1 2$ at 
• States Space $S _ { b }$ . The state $s _ { t } ^ { ( 1 ) } \quad \in \quad S _ { b }$ st observed at time step $t$ is represented by the feature vector $s _ { t } ~ = ~ ( | \Gamma _ { t } ^ { L o c } | , | C _ { t } ^ { L o c } | , N _ { \mathcal { Z } } ^ { \Gamma } , N _ { \mathcal { Z } } ^ { C } , | D | , | T | )$ , where $| \Gamma _ { t } ^ { L o c } |$ and $| C _ { t } ^ { L o c } |$ denote the number of parcels and available couriers to be processed on the local platform, respectively. $N _ { \mathcal { Z } } ^ { \Gamma }$ and $N _ { \mathcal { Z } } ^ { C }$ are the future number of pick-up parcels $\Gamma$ and couriers $C$ of Loc. As supply–demand forecasting is not the primary contribution of this work, we exploit a typical sequence prediction model (e.g., GRU) to predict $N _ { \mathcal { Z } } ^ { \Gamma }$ and $N _ { \mathcal { Z } } ^ { C }$ across all regions $\mathcal { Z }$ of ${ \mathcal { G } } _ { n }$ in a future time slot. $| D |$ captures the average distance between couriers and pick-up tasks (lower values imply closer proximity), while $| T |$ quantifies task urgency relative to the current time and task deadline [9]. 
After determining the batch size, RL-CAPA executes the second-stage policy $\pi _ { 2 } ( a _ { t } ^ { ( 2 ) } \mid s _ { t } , a _ { t } ^ { ( 1 ) } )$ , where $a _ { t } ^ { ( 2 ) }$ a(2)t is the joint cross-or-not decision for all parcels in the current batch. As 
8 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
the batch size $| \Delta \Gamma _ { t } |$ varies across batches, $\cdot$ is factorized over parcels with shared parameters: $\_$ 2 a $\begin{array} { r } { \prod _ { i = 1 } ^ { \vert \Delta \bar { \Gamma _ { t } } \vert } \pi _ { 2 } ( a _ { t , i } \vert s _ { t , i } ^ { ( 2 ) } , a _ { t } ^ { ( 1 ) } ) } \end{array}$ s t,i , 
• Action space $A _ { m }$ . Each parcel is treated as an agent making the cross-or-not decision. Here, $a _ { t } ^ { ( 2 ) } ~ =$ a $( a _ { t , 1 } , a _ { t , 2 } , \ldots , a _ { t , | \Delta \Gamma _ { t } | } )$ , and each binary variable $a _ { t , i } \in$ $\{ 0 , 1 \}$ indicates whether parcel $\tau _ { i }$ is deferred to the next batch $a _ { t , i } = 0$ or sent to the auction pool $a _ { t , i } = 1$ . 
• States space $S _ { m }$ . Each per-parcel state $\cdot$ $S _ { m }$ is a feature vector $\begin{array} { r l r } { s _ { t , i } ^ { ( 2 ) } } & { { } = } & { ( t _ { \tau _ { i } } , t _ { c u r } , v _ { \tau _ { i } } } \end{array}$ st,i , $, | \Delta \Gamma _ { t } | , | C _ { t } ^ { L o c } | , \bar { u } _ { t } ^ { L o c } , | C _ { t } ^ { C r o s s } | , \bar { b } _ { t } ^ { \bar { C } r o s s } , \Delta b )$ Ct , where $t _ { \tau _ { i } }$ is the deadline of parcel $\tau _ { i }$ , $t _ { c u r }$ is the current time, $\cdot$ $\cdot$ is the estimated local net revenue of $\tau _ { i }$ , $| \Delta \Gamma _ { t } |$ and $\cdot$ are the numbers of unassigned parcels and available local couriers, $\cdot$ is the average remaining capacity of local couriers, |CCrosst | is the total number $\cdot$ of available couriers across cooperating platforms, $\bar { b } _ { t } ^ { C r o s s }$ is the moving average of recent cross-platform winning bids, and $\Delta b = a _ { t } ^ { ( 1 ) }$ is the batch size from the first stage. 
After both stages are executed, the environment returns a platform-level total reward 
$$
R _ {t} = \operatorname {R e v} _ {S} ^ {t} \left(\Gamma_ {\text {L o c}}, C _ {\text {L o c}}, \mathcal {P}\right), \tag {8}
$$
which is exactly aligned with the optimization objective of the CPUL problem in Eq. 5. In this way, both stages are optimized toward the same platform-level return rather than heterogeneous local objectives. 
We adopt a policy-gradient framework with two actor networks and two critic networks to train the hierarchical decision process. The first actor $\pi _ { 1 }$ determines the batch timewindow decision, while the second actor $\pi _ { 2 }$ determines the conditional parcel-level cross-or-not decisions. To evaluate the two stages, we introduce two critics: $V _ { 1 } ( s _ { t } ^ { ( 1 ) } )$ , which estimates the long-term return before the first-stage decision is made, and $\cdot$ , which estimates the expected return after the first-stage action has been selected. The first-stage action should be evaluated by how much it improves the downstream decision quality of the second stage. Therefore, the first-stage advantage is defined as 
$$
A _ {t} ^ {(1)} = V _ {2} \left(s _ {t} ^ {(2)}, a _ {t} ^ {(1)}\right) - V _ {1} \left(s _ {t} ^ {(1)}\right), \tag {9}
$$
which captures the contribution of the selected batch timewindow to the expected future return. The first-stage policy is then updated by 
$$
\nabla J _ {1} \left(\theta_ {1}\right) = \mathbb {E} \left[ \nabla \log \pi_ {1} \left(a _ {t} ^ {(1)} \mid s _ {t} ^ {(1)}; \theta_ {1}\right) A _ {t} ^ {(1)} \right]. \tag {10}
$$
The second-stage advantage is defined as 
$$
A _ {t} ^ {(2)} = R _ {t} - V _ {2} \left(s _ {t} ^ {(2)}, a _ {t} ^ {(1)}\right), \tag {11}
$$
which measures whether the second-stage joint action yields a better platform-level outcome than expected under the selected time-window decision. Accordingly, the second-stage policy is updated by 
$$
\nabla J _ {2} \left(\theta_ {2}\right) = \mathbb {E} \left[ \nabla \log \pi_ {2} \left(a _ {t} ^ {(2)} \mid s _ {t} ^ {(2)}, a _ {t} ^ {(1)}; \theta_ {2}\right) A _ {t} ^ {(2)} \right]. \tag {12}
$$
The two critics are trained by minimizing their temporal estimation errors 
$$
L _ {V _ {1}} = \mathbb {E} \left[ \left(V _ {1} \left(s _ {t} ^ {(1)}\right) - \hat {R} _ {t}\right) ^ {2} \right], \tag {13}
$$
$$
L _ {V _ {2}} = \mathbb {E} \left[ \left(V _ {2} \left(s _ {t} ^ {(2)}, a _ {t} ^ {(1)}\right) - \hat {R} _ {t}\right) ^ {2} \right], \tag {14}
$$
where $\hat { R } _ { t }$ is the empirical discounted return. The overall training objective of RL-CAPA is 
$$
\max  _ {\theta_ {1}, \theta_ {2}} J _ {1} \left(\theta_ {1}\right) + J _ {2} \left(\theta_ {2}\right), \quad \min  _ {\phi_ {1}, \phi_ {2}} L _ {V _ {1}} \left(\phi_ {1}\right) + L _ {V _ {2}} \left(\phi_ {2}\right), \tag {15}
$$
where the four networks are updated with independent optimizers, and A(1)t , $\cdot$ are treated as constants in the policygradient updates. 
Regarding RL-CAPA decision updates, we adopt a periodic update scheme: the RL agent collects decision experiences over a fixed number of episodes and then performs one policy update using the collected trajectories. During the parcel assignment process, the RL policy parameters remain frozen and are used only for forward inference to generate decisions. This scheme ensures that the high computational cost of RL training is fully offline and effectively maintains online responsiveness. 
Discussion. The two decisions progress in RL-CAPA, i.e., batch size partitioning and cross-or-not parcel assignment, are closely coupled and mutually affect. The batch size decision directly affects the number and urgency of parcels within each batch. Conversely, the actions of cross-or-not decision, such as delaying to the next batch or entering the auction pool, influence future states observed by batch size partitioning, guiding adaptive adjustments to batch duration. Hence, our hierarchical formulation in RL-CAPA offers two important advantages. First, both stages are explicitly optimized toward the same platform-level objective, i.e., the total revenue of the local platform. Second, the hierarchical policy structure effectively handles the strong dependency between the two stages: the first-stage action shapes the feasible decision space of the second stage, while the second-stage assignment outcome determines the long-term quality of future first-stage decisions. 

TABLE II: Parameter settings of the local platform

<table><tr><td>Parameters</td><td>Values</td></tr><tr><td>φ, Δb</td><td>0.5, 20s</td></tr><tr><td># of couriers |C| (NYTaxi)</td><td>0.1K, 0.2K, 0.3K, 0.4K, 0.5K</td></tr><tr><td># of Parcels |Γ| (NYTaxi)</td><td>0.5K, 2k, 5K, 10K, 20K</td></tr><tr><td># of couriers |C| (Synthetic)</td><td>1K, 2K, 3K, 4K, 5k</td></tr><tr><td># of Parcels |Γ| (Synthetic)</td><td>5k, 20K, 50K, 100K, 200K</td></tr><tr><td>Capacity of courier w</td><td>25, 50, 75, 100, 125</td></tr><tr><td># of cooperating platforms P</td><td>2,4,8,12,16</td></tr><tr><td>The parameter of fixed fare ζ</td><td>0.1, 0.2, 0.3, 0.4, 0.5</td></tr><tr><td>The parameter of threshold ω</td><td>0.5, 0.6, 0.7, 0.8, 0.9, 1.0</td></tr><tr><td>The sharing rate μ1 + μ2 of Loc</td><td>0.5, 0.6, 0.7, 0.8, 0.9, 1.0</td></tr><tr><td>The sharing rates [μ1, μ2]</td><td>[0.2,0.8],[0.3,0.7],[0.4,0.6],[0.5,0.5],[0.6,0.4],[0.7,0.3],[0.8,0.2]</td></tr></table>
9 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 

TABLE III: Parameter settings of cooperating platforms

<table><tr><td rowspan="2" colspan="2">Dataset / Param.</td><td colspan="4">Cooperative platform</td></tr><tr><td>PA</td><td>PB</td><td>PC</td><td>PD</td></tr><tr><td colspan="2">γ</td><td colspan="4">0.5</td></tr><tr><td rowspan="2">NYTaxi</td><td>|WC|</td><td rowspan="2">0.4K, 24,485</td><td rowspan="2">0.5K, 24,884</td><td rowspan="2">0.6K, 24,873</td><td rowspan="2">0.7K, 24,290</td></tr><tr><td>|TC|</td></tr><tr><td rowspan="2">Synthetic</td><td>|WC|</td><td rowspan="2">1.0K, 59,799</td><td rowspan="2">1.5K, 59,558</td><td rowspan="2">2.0K, 63,343</td><td rowspan="2">3.0K, 60,591</td></tr><tr><td>|TC|</td></tr><tr><td>CD</td><td>|TC|</td><td>61,508</td><td>63,297</td><td>75,218</td><td>68,361</td></tr></table>
# IV. EXPERIMENTAL EVALUATION
In this section, we evaluate the efficiency and effectiveness of the proposed methods on both real and synthetic datasets. 
# A. Experimental Setup
Data and parameters. We conduct experiments using two datasets: the NYTaxi dataset1 and a synthetic dataset. The NYTaxi dataset contains one month of taxi trajectory data from New York City. The synthetic dataset is constructed from realworld logistics data across multiple cooperating platforms in Shanghai, simulating parcel pick-up and drop-off activities. We randomly sample parcels and extract pick-up/drop-off points and time information from actual taxi trajectories. The arrival sequence of parcels is simulated based on their order of appearance. For the road network, we use Open-StreetMap data2: Shanghai’s network includes 216,225 edges and 14,853 nodes, while New York’s includes 8,635,965 edges and 157,628 nodes. Since parcel weights are not provided in either dataset, we randomly assign weights from a uniform distribution over (0, 10). Courier preference coefficients $\alpha _ { c _ { P _ { . } } ^ { i } }$ and $\beta _ { c _ { P } ^ { i } }$ are also generated uniformly, following the method in [27]. In practical deployment, these coefficients can be presented as selectable options for couriers and platforms [1]. The deadlines for parcels, $t _ { \tau }$ and $t _ { \psi }$ , are set to range from 0.5 to 24 hours based on real-world scenarios [9], [1]. In the training of RL-CAPA, we split the NYTaxi and Shanghai datasets into $70 \%$ for training and $30 \%$ for testing. We adopt the RMSprop optimizer[35] with a learning rate of 0.001 and a discount factor $\gamma = 0 . 9$ . Both the actor and critic networks are implemented as two-layer multilayer perceptrons (MLPs) with 128 hidden units per layer and ReLU activation functions. The model is trained for at least $1 \times 1 0 ^ { 6 }$ training steps, or until the reward converges. All parameter settings, including default and key values, are summarized in Table II, with key parameters highlighted in bold. 
Compared methods. We compare our proposed algorithms CAPA (standard algorithm) and RL-CAPA (RL-based algorithm) with existing algorithms, including RamCOM [5], MRA [1], and Greedy [9]. 
Evaluation metrics and implements. The performance of the matching algorithms is evaluated using three key metrics: (i) Total Revenue (TR): The combined revenue from both local and cross-platform task completions; (ii) Completion Rate (CR): The ratio of tasks completed (locally and cooperatively) to the total number of local tasks; (iii) Batch Processing Time (BPT): The elapsed time from the beginning of each matching 
round to the completion of all task assignments within that round. All algorithms are implemented in Python and evaluated on a PC equipped with an Intel i7-9700K@3.6GHz CPU and 16GB RAM. 
# B. Performance Evaluation
We examine the performance of our proposed matching methods in the NYTaxi and Synthetic datasets. 
Exp-1: Effect of parcel number $| \Gamma |$ : As shown in Fig. 6(a)(b)(c), the TR of all algorithms increases with the number of tasks |Γ|, though the growth is sublinear in the NYTaxi data. Among the methods, RL-CAPA, CAPA, and RamCom exhibit superior TR, particularly when $| \Gamma |$ exceeds the number of internal couriers, as they effectively leverage external couriers to serve additional requests. Notably, RL-CAPA and CAPA outperform RamCom due to their deferred matching and threshold-based task selection strategies, which prioritize high-value tasks to maximize platform revenue. For $| \Gamma | < 5 \mathrm { k } .$ , CAPA achieves the highest TR and CR. As $| \Gamma |$ increases, the CRs of RL-CAPA, CAPA, and RamCom remain stable initially, as more requests are fulfilled by external couriers. However, when $| \Gamma | > 5 \mathrm { k }$ , their CRs drop significantly due to capacity saturation of both internal and external couriers, limiting further task acceptance. In terms of BPT, all algorithms exhibit increased processing time per batch as $| \Gamma |$ grows. his is because the CAPA and MRA algorithms use multiple rounds of matching, and when the number of packages increases and the time division is larger, the processing time for each batch is longer than that of the RL-CAPA, RamCom, and Greedy algorithms. The Greedy algorithm uses a greedy algorithm, and its processing time is the shortest. The results on revenue and completion ratio are similar to those for the NYTaxi dataset. 
Exp-2: Effect of courier number $| C |$ : From Fig. 6(d)(e)(f) and Fig. 7 (d)(e)(f) , it can be observed that as $| \Gamma |$ increases, both BPT and TR rise for all algorithms, while CR declines. When the number of couriers $| C | < 4 0 0$ in the NYTaxi dataset, the TR, CR, and BPT for all algorithms increase with $| C |$ . This indicates that a larger courier pool enables more pickup tasks to be completed, thereby enhancing both revenue and task fulfillment. More specifically, Fig. 6(g) shows that RL-CAPA and CAPA achieve the most significant revenue growth. Similarly, Fig. 6(h) demonstrates that the CR improves across all algorithms, with RL-CAPA and CAPA achieving relatively higher rates, likely due to their strategies of not rejecting tasks when external policy constraints are considered. Among all methods, CAPA consistently achieves the highest TR and CR. As shown in Fig. 6(i), the BPT slightly increases with $| C |$ , but the impact remains modest, suggesting that all algorithms maintain efficient processing even as the system scales. However, once $| C | > 4 0 0$ , the growth of TR, CR, and BPT tends to plateau. This suggests that the majority of pickup tasks are already being served and that the marginal benefit of adding more couriers diminishes. Thus, after reaching a certain scale, increasing the number of couriers yields limited improvements in platform performance and efficiency. The trends in TR, CR and BPT on the synthetic dataset are consistent with those observed in the NYTaxi dataset. 
10 
1https://www.nyc.gov 
2https://www.openstreetmap.org 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/062bbd3b56f9eac92b8c07210f46a00eb169b403cc3bbb49a16c43189b9e1cb2.jpg)


(a) TR VS. |Γ|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/39499663c79cfea878f2768a00f1f5a95908ca78bb4ae70e3fa609ff3d32eb8a.jpg)


(b) CR VS. |Γ|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/6574e130f10f5e890abc4cacc5806d96eef2dc808e61a1403f7fc83a788e4d0b.jpg)


(c) BPT VS. |Γ|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/ef00eb111e2fb416b0c50e342856b2d456ddd77d811fe368b880f7e01a444d66.jpg)


(d) TR VS. |C|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/3c15a7b2622458ef4587cabeb39d39760630738f8db6bc597f392aa0d6dbb226.jpg)


(e) CR VS. |C|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/e203d6c30fc454ce286a04e2a6e60e3b6e03b23c400d75004271e51db6a60d6d.jpg)


(f) BPT VS. |C|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/a64a4ecb16a878d0936ad36a729da234e57f3186e8c00a0e69e885222e4f7bc4.jpg)


(g) TR VS. rad.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/b2b4ceaee9a749d534eb8b7b3fdc2f2e717041cd9f555b975e7ee14cc64acef7.jpg)


(h) CR VS. rad.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/6654e0dcb4273d65adfbbf9ef83b305bd46975b0af91c677a768841719637d9e.jpg)


(i) BPT VS. rad.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/815e36976e63bbba334bbdff9e4fb72fa951030515940077c404f049d4c2a99e.jpg)


(j) TR VS. $| \mathcal { P } |$

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/f34a5b3b53b4d00bf0533e1b8a6cfdd3f521d7664df7b1d373593fcd95aef007.jpg)


(k) CR VS. |P |

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/3e9637cf498d956e9ef8fb8f5d99627f79f0e12933e9d66f0a433e24af3e9177.jpg)


(l) BPT VS. |P |


Fig. 6: Matching results by varying |Γ|, $| C |$ , rad and $| \mathcal { P } |$ on NYTaxi dataset.

Exp-3: Effect of courier radius |rad.|: Fig.6(g)(h)(i) and Fig.7(g)(h)(i) reports the impact of varying the service radius $| r a d |$ (from $0 . 5 \ \mathrm { k m }$ to $2 . 5 \ \mathrm { k m } ,$ on algorithm performance across both the NYTaxi and Synthetic datasets. Overall, enlarging the service radius leads to increased TR across all algorithms, particularly benefiting RL-CAPA, which consistently outperforms CAPA and other baselines. This advantage is attributed to RL-CAPA’s superior ability to manage cooperative parcel assignments, as a larger service area enables couriers to access and fulfill more requests, thereby boosting platform revenue. In terms of completion ratio (CR), when $| r a d |$ is small (e.g., $\leq 1 . 5 \mathrm { k m } ,$ ), RL-CAPA and CAPA both show steady improvements due to the expanded coverage allowing more parcels to be served by both internal and external couriers. As the radius continues to increase, CR growth tends to stabilize since most parcels have already been matched and delivered. Notably, baseline methods such as MBA and Greedy continue to benefit from increasing $| r a d |$ , likely because the limited number of local couriers gains greater access to parcels over the enlarged area. Batch processing time (BPT) also increases moderately with larger $| r a d |$ , especially for CAPA and MRA, due to the additional overhead in identifying suitable couriers from a broader area. Nevertheless, BPT stabilizes as courier capacity approaches saturation, indicating that the system maintains acceptable efficiency even under expanded operational scopes. Importantly, both datasets exhibit similar performance trends across all metrics, which validates the robustness of the proposed RL-CAPA algorithm under varying urban logistics scenarios. 
Exp-4: Effect of cooperating platform number $| \mathcal { P } |$ : Fig. 6 (j)(k)(l) and Fig. 7 (j)(k)(l) report the effect of cooperating platform number $| \mathcal { P } |$ for cross-based algorithms, i.e., RL-CAPA, CAPA, and RamCOM. Evidently, as the number of cooperating platforms increases, the task completion rate of the local platform significantly improves, eventually approaching $100 \%$ . This is because more cooperating platforms introduce a greater number of available workers, thereby continuously enhancing task fulfillment efficiency. Notably, despite the involvement of additional cooperating platforms, the BPT of all algorithms remains largely unchanged. This can be at-
tributed to the fact that all cooperating platforms participate in independent sealed-bid auctions, where bidding is conducted without cross-platform interactions, making the number of platforms have minimal impact on BPT. Furthermore, when a large number of cooperating platforms are involved, the task completion rates of all algorithms approach $100 \%$ . However, under such conditions, CAPA achieves higher total platform revenue compared to RamCOM. This is due to its use of delayed matching and threshold-based task selection strategies, which prioritize high-value tasks to maximize platform profits. In contrast, RL-CAPA outperforms the heuristic-based CAPA in terms of platform revenue, as its reinforcement learning approach can handle more complex matching scenarios and optimize task allocation quality from a long-term perspective. 
Exp-5: Comparison of RL-based methods in model training: To further analyze the contribution of different decision components in RL-CAPA, we conduct ablation studies with the following variants: 
Batch-CAPA: optimizing batch partitioning, and adopting the cross-platform decision strategy from CAMA; 
Auction-CAPA: optimizing only cross-platform decisions, with the default batch configuration. 
As shown in Fig. 9, we plot the TR curves during training on both datasets to illustrate the learning process of the RL model. The results show that the TR of all RL-based methods increases steadily and converges after approximately $0 . 6 \substack { - 0 . 8 } \times 1 0 ^ { 6 }$ training steps, demonstrating the effectiveness and convergence of the proposed approach. The ablation results further indicate that RL-CAPA achieves the highest final TR, while Batch-CAPA converges faster. This is because Batch-CAPA has a smaller action space by optimizing only batch partitioning, leading to faster convergence but limited performance gains due to the lack of cross-platform decision capability. Although Auction-CAPA can optimize crossplatform assignment, its fixed batch configuration limits its adaptability in dynamic environments. In contrast, RL-CAPA jointly optimizes both decisions, enabling adaptive strategies under varying workloads and achieving superior overall performance. 
11 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/a753ee3d9cdee351c6ce16aa9a7884c7ddd2a428905c8d29e115d6b970dd939f.jpg)


(a) TR VS. |Γ|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/38b95f86f7cadd65577c35bb281950c1ccc9ca768e7f0dc0ad3b69ec69e13b90.jpg)


(b) CR VS. |Γ|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/ba069e1e8a76fdae12efc6bb49882a1db9d1d1a89d43b7811eedaa13330142ed.jpg)


(c) BPT VS. |Γ|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/11dcf228e7dbcd144c837eeb0afabde193766a3f680e0bd048877ddbec441532.jpg)


(d) TR VS. |C|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/c6a172963c847defee81337dd42e741a2fba860fbfbf4bc7d84dc77ec1c72e6d.jpg)


(e) CR VS. |C|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/06c2a8a3c7c65403eabeb334b24fce6e814aabe19bc3733421dfc6b72e1b9066.jpg)


(f) BPT VS. |C|

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/360aa42c1ffa5ac87a3dc4f42f6ffb7f8467b9853265f5590372ee8f4ef290f1.jpg)


(g) TR VS. rad.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/a6048606889ce81f89ecaeb8f047139671bcb28bd403776f95568c2c092a5a95.jpg)


(h) CR VS. rad.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/d56eee47160dae83e8228d381c0b36f05d02ebd8c52c1085f19f8fd7e6f7fb35.jpg)


(i) BPT VS. rad.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/81667ce1e8740b3f0251e9c30a5905c5af6c1371c71a1649272e38f652842f8f.jpg)


(j) TR VS. |P |

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/f33f5ce21e35a42041b49d76f716bb284e3d3df5b5fa65ea90e444d05b0a5c87.jpg)


(k) CR VS. |P |

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/1794c11aeaea9af9bac7ba6fe229f766a7ec79bc619c30d5720fe5ef722af7c6.jpg)


(l) BPT VS. |P |


Fig. 7: Matching results by varying $| \Gamma | , | C |$ , rad and $| \mathcal { P } |$ on synthetic datasets.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/ca652de1beb74e0f761145d29d0e0c737b8af76c9cb91ffb62a8998a814f985b.jpg)


(a) Default VS. TR

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/912073261fd8026dcf0d78d936614615590580ed88ed08a8c21f47bbc2d1fdaf.jpg)


(b) Default VS. CR

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/19ed0ab5c8ea63ab385d2288cda578f698fa2a8f7d1e706f2fb50b5928db27ab.jpg)


(c) Default VS. BPT


Fig. 8: Matching results under default settings on NYTaxi and synthetic datasets.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/e8a009794c3a824282f29456cb662cf01f70b430db35613c412b6dac75a805cf.jpg)


(a) Chengdu datasets

![image](https://cdn-mineru.openxlab.org.cn/result/2026-04-25/0cafc836-ab04-4139-82b4-0e6e209cd8cc/ed4758e931f38991bbb29b3766e20fda2d51ad6bca29cf0b4279436c2182139e.jpg)


(b) Haikou datasets


Fig. 9: Comparison of RL-based methods in model training.

Exp-5: Results under default settings: As reported in Fig. 8, under default experimental settings in the NYTaxi dataset, RL-CAPA consistently outperforms all baselines across key metrics. Specifically, in terms of CR, it achieves a relative improvement of $1 . 8 6 \%$ over CAPA and $1 2 . 3 3 \%$ , $2 6 . 1 5 \%$ , and $3 6 . 6 7 \%$ over RamCom, MRA, and Greedy, respectively. In terms of TR, RL-CAPA improves upon CAPA by $1 . 8 2 \%$ , RamCom by $1 0 . 1 9 \%$ , and MRA and Greedy by $3 8 . 4 1 \%$ and $5 3 . 3 4 \%$ , respectively. Despite its learning-based decision-making, RL-CAPA maintains a low batch processing time of 0.08s, which is $60 \%$ faster than CAPA and comparable to other baselines. These results demonstrate that RL-CAPA not only enhances assignment effectiveness and economic returns but also ensures high computational efficiency, making it well-suited for real-time cooperative logistics scenarios. Similar experimental results on the Synthetic dataset also support the superiority of the proposed methods RL-CAPA and CAPA in terms of efficiency and effectiveness. 
In summary, the two proposed algorithms, i.e., CAPA and RL-CAPA, suit different application scenarios. RL-CAPA is recommended for environments with high real-time requirements and large task volumes, while CAPA is better suited for scenarios with lower real-time demands and smaller task scales. Both algorithms effectively achieve resource allocation. 
# V. LITERATURE REVIEW
In this section, we survey the related works of task assignment and auction mechanisms. 
# A. Task Assignment
In SC, online task assignment refers to the process of finding suitable service providers for sequentially arriving tasks [36], [37], [2], [9], [5]. 
Recent years have witnessed significant progress in task assignment for spatial crowdsourcing (SC). However, most existing studies focus on single-platform settings [2], [1], [24], [3], which always face the bottleneck of uneven distribution of tasks and workers. To this end, recent efforts have shifted toward multi-platform cooperation [5], [30], [12], [38]. Cheng et al. [5] introduced the concept of Cross-Online Matching, enabling platforms to leverage idle workers from cooperating platforms to improve matching efficiency. Yang et al. [30] developed a Batch-based Collaborative Task Allocation method to reduce the uneven distribution of tasks and workers across multiple platforms. These approaches have shown the effectiveness of multi-platform cooperation in alleviating supply–demand imbalance. However, they often overlook a critical issue, namely how to properly incentivize self-interested platforms to participate in cooperation. Li et al. [12] designed an auction-based incentive mechanism to encourage platforms to rent out their idle workers to other platforms, thereby increasing their own profits. 
Although the above methods effectively improve the efficiency of task assignment, they still face challenges in handling dynamic task arrival patterns and optimizing longterm performance across platforms. Hence, the role of reinforcement learning in SC has gained increasing attention in 
12 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 
task assignment [39], [40], [41], [9]. Shan et al. [39] proposed a deep reinforcement learning framework for crowdsourcing task scheduling, focusing on long-term reward estimation. Tong et al. [40] introduced a learning-to-dispatch system that integrates RL and combinatorial optimization for large-scale taxi dispatching. These methods have made great efforts to effectively optimize task assignment in SC, they do not incorporate incentive mechanisms or strategic interactions among multiple platforms. Li et al. [9] proposed a DRL-based method to dynamically adjust sliding window sizes, improving task matching. However, in the CPUL problem, the batch division determines the number of candidate tasks to be matched, which directly affects the willingness of the cooperating platform to participate in cross-platform cooperation, making the task assignment decision-making process more complex. 
The above studies have provided significant efforts toward addressing the CPUL problem by improving matching efficiency and promoting cross-platform cooperation. However, how to optimize such matching among cooperating platforms, their associated workers, and dynamic tasks to maximize the long-term revenue of the local platform under complex and dynamic logistics systems is still an open problem. 
# B. Auction Mechanism
Auction models have emerged as innovative mechanisms that efficiently motivate bidders to bid truthfully for items. They have already been explored in SC to incentivize similar service providers to cooperate in task assignment. 
Auction models, critical incentive mechanisms, have attracted widespread attention for task assignment in SC, with recent research findings exploring auction models from different perspectives [1], [42], [43], [25]. Li et al. [1] proposed an Auction-Based Crowdsourcing FLML problem, in which the platform allocates tasks based on courier preferences to maximize social welfare for both the platform and couriers. Wei et al. [25] presented a new honest double auction framework to ensure the authenticity of auctions in complex scenarios. These methods effectively incentivize workers to perform tasks. However, as they focus on two-side matching within a single platform, still sufferring from the imbalance between supply and demand. Hu et al. [42] introduced a mobile crowdsourcing incentive mechanism combining reverse and multi-attribute auctions, aiming to enhance participation. Yang et al. [43] designed a decision-making mechanism based on Stackelberg games, proving the existence of a unique equilibrium that maximizes utility. These approaches extend auction design to multi-platform settings and incentivize cooperation among platforms in task assignment. However, they predominantly focus on single-layer auction mechanisms and do not account for the two-layer auctions of the CPUL problem, where both cooperating platforms and their couriers participate in separate but interrelated bidding processes. As a result, existing auction models are insufficient to support the dual-layer bidding requirements inherent in cross-platform parcel allocation. 
# VI. CONCLUSION AND FUTURE WORK
In this paper, we propose the CAPA framework to address the CPUL problem. This framework effectively alleviates 
the issue of spatiotemporal imbalance between parcels and couriers. Specifically, we design a baseline algorithm, i.e., CAPA, to address the CPUL algorithm to maximize the local platform’s revenue while promoting efficient and fair resource allocation across platforms. Additionally, we introduce the RL-CAPA algorithm to further optimize global parcel assignment strategies. Extensive experimental results on NYTaxi and Synthetic datasets demonstrate the effectiveness and efficiency of our proposed algorithms. 
As for future work, we plan to extend this work in two directions: First, large language models (LLMs) can provide effective guidance for the intelligent decisions made by the customized model RL-CAPA. We thus plan to develop an efficient solution that integrates LLMs with a customized model to collaboratively address the CUPL problem, which further enhances the revenue of cooperating platforms. Second, privacy protection is an important concern in multi-platform collaboration. Accordingly, in future work, we will explore the integration of advanced approaches, such as federated learning and differential privacy, to enhance privacy preservation in cross-platform cooperation. 
# REFERENCES


[1] Y. Li, Y. Li, Y. Peng, X. Fu, J. Xu, and M. Xu, “Auction-based crowdsourced first and last mile logistics,” IEEE Transactions on Mobile Computing, vol. 23, no. 1, pp. 180–193, 2022. 




[2] Y. Li, Y. Pan, G. Zhu, S. He, M. Xu, and J. Xu, “Charging-aware task assignment for urban logistics with electric vehicles,” IEEE Transactions on Knowledge and Data Engineering, vol. 37, no. 7, pp. 3947–3961, 2025. 




[3] K. Xia, L. Lin, S. Wang, H. Wang, D. Zhang, and T. He, “A predictthen-optimize couriers allocation framework for emergency last-mile logistics,” in Proceedings of the 29th ACM SIGKDD Conference on Knowledge Discovery and Data Mining, pp. 5237–5248, 2023. 




[4] F. M. Bergmann, S. M. Wagner, and M. Winkenbach, “Integrating first-mile pickup and last-mile delivery on shared vehicle routes for efficient urban e-commerce distribution,” Transportation Research Part B: Methodological, vol. 131, pp. 26–62, 2020. 




[5] Y. Cheng, B. Li, X. Zhou, Y. Yuan, G. Wang, and L. Chen, “Real-time cross online matching in spatial crowdsourcing,” in 2020 IEEE 36th international conference on data engineering, pp. 1–12, 2020. 




[6] “Cainiao.” https://www.caoniao.com. 




[7] “JD Logistics.” https://www.jdl.com/. 




[8] “Amazon.” https://www.amazon.com. 




[9] Y. Li, Q. Wu, X. Huang, J. Xu, W. Gao, and M. Xu, “Efficient adaptive matching for real-time city express delivery,” IEEE Transactions on Knowledge and Data Engineering, vol. 35, no. 6, pp. 5767–5779, 2023. 




[10] X. Feng, F. Chu, C. Chu, and Y. Huang, “Crowdsource-enabled integrated production and transportation scheduling for smart city logistics,” International Journal of Production Research, vol. 59, no. 7, pp. 2157– 2176, 2021. 




[11] O. Stopka, K. Jeˇrabek, and M. Stopkov ´ a, “Using the operations research ´ methods to address distribution tasks at a city logistics scale,” Transportation Research Procedia, vol. 44, pp. 348–355, 2020. 




[12] B. Li, Y. Cheng, Y. Yuan, C. Li, Q. Jin, and G. Wang, “Competition and cooperation: Global task assignment in spatial crowdsourcing,” IEEE Transactions on Knowledge and Data Engineering, vol. 35, no. 10, pp. 9998–10010, 2023. 




[13] T. Ren, X. Zhou, and et al., “Efficient cross dynamic task assignment in spatial crowdsourcing,” in 2023 IEEE 39th International Conference on Data Engineering, pp. 1420–1432, 2023. 




[14] Y. Huang, X. Qiao, J. Tang, P. Ren, L. Liu, C. Pu, and J. Chen, “An integrated cloud-edge-device adaptive deep learning service for crossplatform web,” IEEE Transactions on Mobile Computing, vol. 22, no. 4, pp. 1950–1967, 2021. 




[15] X. Kong, X. Liu, B. Jedari, M. Li, L. Wan, and F. Xia, “Mobile crowdsourcing in smart cities: Technologies, applications, and future challenges,” IEEE Internet of Things Journal, vol. 6, no. 5, pp. 8095– 8113, 2019. 


13 
JOURNAL OF LATEX CLASS FILES, VOL. 14, NO. 8, AUGUST 2021 


[16] G. Ke, H.-L. Du, and Y.-C. Chen, “Cross-platform dynamic goods recommendation system based on reinforcement learning and social networks,” Applied Soft Computing, vol. 104, p. 107213, 2021. 




[17] B. Li, Y. Cheng, Y. Yuan, Y. Yang, Q. Jin, and G. Wang, “Acta: autonomy and coordination task assignment in spatial crowdsourcing platforms,” Proceedings of the VLDB Endowment, vol. 16, no. 5, pp. 1073–1085, 2023. 




[18] Z. Liu, G. Xiao, X. Zhou, Y. Qin, Y. Gao, and K. Li, “Cross online assignment of hybrid task in spatial crowdsourcing,” in 2024 IEEE 40th International Conference on Data Engineering, pp. 317–329, 2024. 




[19] G. Zhu, Y. Li, S. Du, J. Xu, S. Ding, and M. Xu, “Aggregative online task assignment in spatial crowdsourcing: An auction-aware approach,” IEEE Transactions on Mobile Computing, vol. 25, no. 3, pp. 3998–4012, 2026. 




[20] A. C. Mckinnon, “A communal approach to reducing urban traffic levels,” Kuhne Logistics University: Hamburg, Germany ¨ , 2016. 




[21] E. Pourrahmani and M. Jaller, “Crowdshipping in last mile deliveries: Operational challenges and research opportunities,” Socio-Economic Planning Sciences, vol. 78, p. 101063, 2021. 




[22] Y. Zeng, Y. Tong, and L. Chen, “Last-mile delivery made practical: An efficient route planning framework with theoretical guarantees,” Proceedings of the VLDB Endowment, vol. 13, no. 3, pp. 320–333, 2019. 




[23] X. Zhan, W. Szeto, C. Shui, and X. M. Chen, “A modified artificial bee colony algorithm for the dynamic ride-hailing sharing problem,” Transportation Research Part E: Logistics and Transportation Review, vol. 150, p. 102124, 2021. 




[24] Y. Li, H. Li, X. Huang, J. Xu, Y. Han, and M. Xu, “Utility-aware dynamic ridesharing in spatial crowdsourcing,” IEEE Transactions on Mobile Computing, vol. 23, no. 2, pp. 1066–1079, 2024. 




[25] Y. Wei, Y. Zhu, H. Zhu, Q. Zhang, and G. Xue, “Truthful online double auctions for dynamic mobile crowdsourcing,” in 2015 IEEE Conference on Computer Communications (INFOCOM), pp. 2074–2082, 2015. 




[26] A. Suzdaltsev, “Distributionally robust pricing in independent private value auctions,” Journal of Economic Theory, vol. 206, p. 105555, 2022. 




[27] I. Krontiris and A. Albers, “Monetary incentives in participatory sensing using multi-attributive auctions,” International Journal of Parallel, Emergent and Distributed Systems, vol. 27, pp. 317–336, 2012. 




[28] H. Fang and S. Morris, “Multidimensional private value auctions,” Journal of Economic Theory, vol. 126, no. 1, pp. 1–30, 2006. 




[29] J. Pinkse and G. Tan, “The affiliation effect in first-price auctions,” Econometrica, vol. 73, no. 1, pp. 263–277, 2005. 




[30] Y. Yang, Y. Cheng, Y. Yang, Y. Yuan, and G. Wang, “Batch-based cooperative task assignment in spatial crowdsourcing,” in 2023 IEEE 39th International Conference on Data Engineering, pp. 1180–1192, 2023. 




[31] Y. Tong, Y. Zeng, B. Ding, L. Wang, and L. Chen, “Two-sided online micro-task assignment in spatial crowdsourcing,” IEEE Trans. Knowl. Data Eng., vol. 33, no. 5, pp. 2295–2309, 2021. 




[32] J. Yao, L. Yang, and et al., “Online dependent task assignment in preference aware spatial crowdsourcing,” IEEE Transactions on Services Computing, vol. 16, no. 4, pp. 2827–2840, 2023. 




[33] Y. Wang, Y. Tong, and et al., “Adaptive dynamic bipartite graph matching: A reinforcement learning approach,” in 2019 IEEE 35th international conference on data engineering, pp. 1478–1489, 2019. 




[34] H. W. Kuhn, “The hungarian method for the assignment problem,” Naval research logistics quarterly, vol. 2, no. 1-2, p. 83–97, 1955. 




[35] R. Elshamy, O. Abu-Elnasr, M. Elhoseny, and S. Elmougy, “Improving the efficiency of rmsprop optimizer by utilizing nestrove in deep learning,” Scientific Reports, vol. 13, no. 1, p. 8814, 2023. 




[36] Y. Li, H. Li, B. Mei, X. Huang, J. Xu, and M. Xu, “Fairness-guaranteed task assignment for crowdsourced mobility services,” IEEE Transactions on Mobile Computing, vol. 23, no. 5, pp. 5385–5400, 2023. 




[37] Y. Zhao, K. Zheng, Z. Wang, L. Deng, B. Yang, T. B. Pedersen, C. S. Jensen, and X. Zhou, “Coalition-based task assignment with priorityaware fairness in spatial crowdsourcing,” The VLDB Journal, vol. 33, no. 1, pp. 163–184, 2024. 




[38] Y. Wang, Y. Tong, Z. Zhou, Z. Ren, Y. Xu, G. Wu, and W. Lv, “Fed-ltd: Towards cross-platform ride hailing via federated learning to dispatch,” in Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining, pp. 4079–4089, 2022. 




[39] C. Shan, N. Mamoulis, R. Cheng, G. Li, X. Li, and Y. Qian, “An end-to-end deep rl framework for task arrangement in crowdsourcing platforms,” in 2020 IEEE 36th International Conference on Data Engineering, pp. 49–60, 2020. 




[40] Y. Tong, D. Shi, Y. Xu, W. Lv, Z. Qin, and X. Tang, “Combinatorial optimization meets reinforcement learning: Effective taxi order dispatching 




at large-scale,” IEEE Transactions on Knowledge and Data Engineering, vol. 35, no. 10, pp. 9812–9823, 2021. 




[41] M. Zhou, J. Jin, W. Zhang, Z. Qin, Y. Jiao, C. Wang, G. Wu, Y. Yu, and J. Ye, “Multi-agent reinforcement learning for order-dispatching via order-vehicle distribution matching,” in Proceedings of the 28th ACM International Conference on Information and Knowledge Management, pp. 2645–2653, 2019. 




[42] A. Mehta et al., “Online matching and ad allocation,” Foundations and Trends® in Theoretical Computer Science, vol. 8, no. 4, pp. 265–368, 2013. 




[43] D. Yang, G. Xue, X. Fang, and J. Tang, “Crowdsourcing to smartphones: Incentive mechanism design for mobile phone sensing,” in Proceedings of the 18th annual international conference on Mobile computing and networking, pp. 173–184, 2012. 


14 