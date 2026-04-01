# Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics

Guanglei Zhu, Jiawen Zhang, Shuo He, Xuhui Song, Yafei Li, Jiangliang Xu, Mingliang Xu 

Abstract—The rapid growth of e-commerce and mobile internet has created significant opportunities for crowdsourced First and Last Mile Logistics (FLML) services. In these services, couriers can collect pick-up parcels while delivering drop-off parcels. Recently, an emerging service paradigm involving parcel sharing across multiple platforms has gained traction, effectively addressing the issue of uneven parcel distribution in independent platforms. However, two key challenges remain: (i) incentivizing cooperating platforms and their couriers to participate in cross-platform parcel assignment, and (ii) adaptively optimizing parcel assignments to maximize overall revenue. In this paper, we investigate the novel Cross-Platform Urban Logistics (CPUL) problem, which seeks to identify optimal courier assignments for pick-up parcels in a cooperative framework. To encourage participation in cross-platform parcel sharing, we propose a double-layer auction model that integrates a First-Price Sealed Auction for cross-platform couriers with a Reverse Vickrey Auction for cooperating platforms. Additionally, we introduce a cross-aware parcel assignment framework to address the CPUL problem by maximizing revenue for the local platform. This framework employs a dynamic threshold-based parcel assignment method, which allocates parcels to a shared pool for cross-task matching based on adaptive thresholds. It further incorporates a dual-stage adaptive optimization strategy to determine optimal batch sizes and decide whether parcels are assigned locally or cooperatively within each batch. Extensive experiments on two real-world datasets demonstrate the effectiveness and efficiency of the proposed methods. 

Index Terms—Location-based service, task assignment, auction model, cross-platform service, urban logistics. 

# 1 INTRODUCTION

W ITH the rapid development of e-commerce and spa-tial crowdsourcing technologies, crowdsourced ur- tial crowdsourcing technologies，crowdsourced urban logistics has emerged as an efficient and cost-effective solution to address the dynamic and complex urban logistics. Urban logistics systems typically provide two core services under the framework of First and Last Mile Logistics (FLML): first-mile logistics, which involves transporting customer parcels to transfer stations; and last-mile logistics, which delivers parcels from transfer stations to customers [5], [21], [41], [42]. In this operational framework, couriers depart from transfer stations with parcels destined for customers. Concurrently, the logistics platform dynamically assigns suitable couriers to collect parcels based on real-time conditions. Owing to its significant contributions to enhancing logistics efficiency and reducing operational costs, crowdsourced urban logistics has attracted considerable attention from both academia [4], [6], [21], [25] and industry (e.g., Cainiao [2], JD [3], and Amazon [1]). 

A central challenge in crowdsourced urban logistics is online parcel assignment, which seeks to optimize the matching of couriers with parcels. In the literature, most existing studies focus on optimizing parcel assignment within a single platform [21], [22]. However, recent statistics [21] indicate that $6 7 . 6 \%$ of respondents demand timely delivery (e.g., within 30 minutes) of their parcels (e.g., fresh goods), highlighting the limitations of uneven spatiotemporal dis-

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/4d381bde0dcf0e431686a48520498b96a06511cd632ad24ce56d33841a18d54d.jpg)



Fig. 1. A toy example of cross-aware parcel assignment.


tribution of parcels and couriers in a single platform, particularly during peak hours, which reduces the overall quality of urban logistics services [9], [17], [31], [33]. In a city, there are typically multiple logistics platforms, each establishing service regions across the city and offering similar logistics services. Consequently, cooperative urban logistics, where couriers from other platforms (called cross-platform couriers, or cross couriers in short) are aggregated to complete parcel services for the local platform, significantly enhances the efficiency of crowdsourced FLML services. When the local platform faces a shortage of couriers to serve parcels, couriers from other platforms may be available. This approach is inspired by an emerging cooperative business model, illustrated by the following toy example. 

Example 1. As illustrated in Fig. 1, consider a scenario with two local-platform couriers, $c _ { 1 } , \ : c _ { 2 } ,$ , three local-platform parcels τ1, τ2, τ3, and a cross-platform courier $c _ { 3 }$ , where each parcel can only be matched with couriers within its search range 

(depicted as dashed circles). There are two parcel assignment strategies: (1) Single-platform parcel assignment, where couriers are restricted to handling parcels within their own platform. As shown in Fig. 1(a), the optimal local-platform matching plan is $M _ { 1 } = \{ ( c _ { 1 } , \bar { \tau } _ { 1 } ) , ( c _ { 2 } , \tau _ { 2 } ) \}$ . (2) Cross-platform parcel assignment, where parcels can also be assigned to couriers from cooperating platforms. The optimal cross-aware matching plan, as depicted in Fig. 1(b), is $M _ { 2 } { \stackrel { . } { = } } \{ ( c _ { 1 } , \tau _ { 1 } ) , ( c _ { 2 } , \tau _ { 2 } ) , ( c _ { 3 } , \tau _ { 3 } ) \}$ . Obviously, crossplatform parcel assignment can complete more parcels as more couriers are involved. 

Drawing on the above, leveraging available couriers from other platforms in a cooperative manner can effectively address the challenge of uneven parcel and courier distribution within the local platform [11], [12], [14], [18], [24]. To this end, Cheng et al. [6] explored real-time crossaware matching in spatial crowdsourcing, which nhances resource distribution balance through information sharing across platforms. Wu et al. [40] employed multi-objective optimization methods to achieve optimal task assignment in cross-platform scenarios. Although these studies provide valuable insights into optimizing task assignment, they typically assume that cooperating platforms (also referred to as cross-platforms) unconditionally accept cross-platform tasks, thereby overlooking the need to design effective incentive mechanisms for cross-platforms and their couriers. To bridge this gap, we investigate the Cross-Platform Urban Logistics (CPUL) problem, which focuses on maximizing the overall revenue of the local platform by dynamically leveraging cross couriers in a cooperative yet self-interested manner. In the CPUL problem, the local platform can temporarily hire cross-couriers from other platforms to perform its parcel services, while ensuring that these cooperating platforms are adequately incentivized. However, addressing the CPUL problem is non-trivial and involves two key challenges: (1) Since couriers are affiliated with different and self-interested cooperating platforms, the first challenge is how to design effective incentive mechanisms to encourage active participation of cross-platforms and their couriers in local parcel assignment. (2) Parcel assignment is a dynamic, large-scale combinatorial optimization problem. Thus, the second challenge is how to efficiently and adaptively determine optimal parcel assignments within the local platform under parcel and courier constraints. 

To address these challenges, we propose a Cross-Aware Parcel Assignment (CAPA) framework, which effectively and efficiently resolves the CPUL problem. First, since auction mechanisms are widely adopted for ensuring fair transactions and protecting bidder interests, we develop the Dual-Layer Auction Model (DLAM) to tackle the first challenge. Specifically, for a given cross-platform parcel, DLAM employs the First-Price Sealed Auction (FPSA) among crossplatform couriers to select the optimal courier for each cooperating platform. It then leverages the Reverse Vickrey Auction (RVA) among cooperating platforms to identify the optimal bidder. The winning courier of a cooperating platform is tasked with completing the assigned parcel. Second, the size of the parcel matching batch (also referred to as the time window) and the decision to assign a parcel to cooperating platforms can significantly impact the quality of parcel assignment. To deal with the second challenge, we propose a dual-stage adaptive parcel assignment method, 

named Reinforcement Learning Cross-Aware Parcel Assignment (RL-CAPA in short), which adaptively determines the optimal batch size and whether parcels should be assigned to cross platforms. Our main contributions are summarized as follows: 

• We formally define the novel CPUL problem that assigns parcels to optimal couriers to maximize the overall revenue of the local platform. We also prove the computational hardness of the CPUL problem. 

• We develop a cross-aware DLAM model, integrating a fair bidding mechanism for cooperating platforms and cross-couriers. We theoretically demonstrate that the DLAM auction model implemented by our proposed algorithms ensures truthfulness, individual rationality, profitability, and computational efficiency. 

• We propose the CAPA framework to address the CPUL problem, which combines an effective heuristic method and an adaptive method to optimize parcel assignment quality. 

• Extensive experiments on two datasets validate the effectiveness and efficiency of our proposed methods. 

The rest of the paper is organized as follows: Section 2 introduces the CPUL problem. Section 3 presents the proposed framework. Section 4 discusses the experiments and results. Section 5 reviews the related work. Section 6 concludes and outlines our future work. 


TABLE 1 Notation and Description


<table><tr><td>Notations</td><td>Description</td></tr><tr><td>P</td><td>a set of cooperating platforms</td></tr><tr><td>Loc</td><td>the local platform</td></tr><tr><td>H</td><td>a set of stations</td></tr><tr><td>Ψ</td><td>a set of drop-off parcels</td></tr><tr><td>Γ</td><td>a set of pick-up parcels</td></tr><tr><td>C</td><td>a set of couriers</td></tr><tr><td>M</td><td>a matching plan</td></tr><tr><td>Lc</td><td>the schedule of a courier c</td></tr><tr><td>BF(c,τ)</td><td>the bidding function in FPAS</td></tr><tr><td>BR(P,τ)</td><td>the bidding function in RVA</td></tr></table>

# 2 PROBLEM FORMULATION

In this section, we first present the system model and the auction model, followed by the definitions of relevant preliminaries. Subsequently, we formulate the CPUL problem. The main notations used in this paper are summarized in Table 1. 

# 2.1 System Model

In our system model, couriers are responsible for completing a certain number of daily drop-off parcels while also collecting real-time pick-up requests [21], [26], [30]. There are two types of platforms in the system, i.e., the local platform Loc and a set of cooperating platforms $\mathcal { P } = \{ P _ { 1 } , \cdots , P _ { k } \}$ . It performs parcel assignment in two steps: local-platform assignment and cross-platform assignment. The pipeline of the system model is depicted in Fig. 2: given a set of arriving parcels $\textcircled{1}$ , the local platform first checks for available couriers and assigns parcels to the most suitable ones $( \textcircled{2} )$ . If there is no available courier, the local platform broadcasts the parcel information to cooperating platforms and selects the most appropriate cross-platform courier via the proposed auction model $\textcircled{3} \textcircled{3}$ (will be detailed in Section 2.2). 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/b0299885eece4b937856a12181f0cda8d5d14483db4f8b361486b387277a04f3.jpg)



Fig. 2. The pipeline of the system model.


We model our system on a road network, represented by the undirected graph $\mathcal { G } _ { n } = ( V _ { n } , E _ { n } ) .$ , where $V _ { n }$ is a set of locations and $E _ { n }$ is a set of roads. Each road $e _ { i j } \in E _ { n }$ connects two locations, $l _ { i }$ and $l _ { j }$ $( l _ { i } , l _ { j } \in V _ { n } )$ , and the weight of $e _ { i j }$ corresponds to the travel distance $d ( l _ { i } , l _ { j } )$ , which is the shortest path distance between $l _ { i }$ and $l _ { j }$ . In addition, we establish a network of logistics stations for each platform (including local platform and cooperating platforms), denoted as $\mathcal { H } ,$ , to provide the crowdsourced FLML service across the city. Each station $h \in \mathcal H$ is represented as a triple $\boldsymbol { h } = ( l _ { h } , \mathcal { C } _ { h } , \mathcal { R } _ { h } ) .$ , where $l _ { h }$ is the location of $h , \mathcal { C } _ { h }$ is a set of couriers managed by the station, and $\mathcal { R } _ { h }$ is the service area. In what follows, we give the definitions of drop-off parcel, pick-up parcel, and courier. 

Definition 1 (Drop-off parcel). A drop-off parcel $\psi \in \Psi ,$ denoted as a triple $\bar { \psi } = ( \bar { l _ { \psi } } , t _ { \psi } , w _ { \psi } )$ , requires capacity $w _ { \psi }$ and should be delivered at drop-off location $l _ { \psi }$ before deadline $t _ { \psi }$ . 

Definition 2 (Pick-up parcel). A pick-up parcel $\tau \in \Gamma$ is represented as a quadruple $\tau = ( l _ { \tau } , \dot { t } _ { \tau } , w _ { \tau } , \dot { p } _ { \tau } ) ,$ , where $w _ { \tau }$ is the required capacity and $p _ { \tau }$ is the fare, $l _ { \tau }$ is the pick-up location and $t _ { \tau }$ is the pick-up deadline. 

Following existing studies [21], [46], we assume that the processing time for each parcel, $\tau$ or $\psi ,$ is negligible, i.e., once the courier reaches the pick-up location $l _ { \tau }$ or $l _ { \phi . }$ , the parcel $\tau$ or $\psi$ is considered to be completed. Besides, the parcel required capacity ${ \bf \nabla } _ { w _ { \tau } }$ or $w _ { \psi }$ ) represents the actual volume or weight of the parcel. Since both dimensions are easily convertible, we treat them interchangeably and consistently use weight as the measure. It is important to note that in our system model, couriers get basic salaries by completing a certain number of daily drop-off parcels and earn additional bonuses for collecting pick-up parcels. Since the goal of the CPUL problem is to maximize the local platform’s overall revenue, we focus on finding the best task assignment between pick-up parcels and couriers in this paper. 

Definition 3 (Courier). A courier $c \in C$ is represented as a six-entry tuple $c = \left( l _ { c } , w _ { c } , t _ { c } , h _ { c } , \Psi _ { c } , \Gamma _ { c } \right)$ , where $l _ { c }$ is the current location of c, $w _ { c }$ is the maximum capacity, $t _ { c }$ is the deadline to return to the attached station $h _ { c } , \Psi _ { c }$ and $\Gamma _ { c }$ are a set of assigned drop-off parcels and a set of pick-up parcels, respectively. 

There are two types of couriers who complete the pickup parcels of the local platform: inner couriers, who belong to the local platform; and cross-platform (cross in short) couriers, who are managed by cooperating platforms. We explain that $w _ { c }$ is the maximum capacity that courier $c$ could hold parcels simultaneously in his/her delivery box. Given 

a courier with a set of assigned pick-up parcels $\Gamma _ { c }$ and a set of drop-off parcels $\Psi _ { c } ,$ his/her schedule $L _ { c } = ( l _ { 1 } , \cdots , l _ { k } )$ is represented as a time-based sequence of locations, where $l _ { k }$ denotes the location of either a pick-up parcel or a dropoff parcel. A valid schedule $L _ { c }$ should satisfy the following constraints: 

• Capacity constraint: The total weight of parcels in $\Psi _ { c }$ and $\Gamma _ { c }$ must always satisfy $\begin{array} { r } { \sum _ { \psi \in \Psi _ { c } } w _ { \psi } + \sum _ { \tau \in \Gamma _ { c } } w _ { \tau } \le w _ { c } , } \end{array}$ i.e., the courier’s delivery box capacity $w _ { c }$ . 

• Deadline constraint: The assigned courier $c$ must arrive at $l _ { \tau }$ and $l _ { \phi }$ $( \tau \in \Gamma _ { c }$ and $\phi \in \Psi _ { c } )$ before both parcel deadline (i.e., $t _ { \tau }$ and $t _ { \psi }$ ) and courier deadline $t _ { c }$ . 

• Invariable constraint: One parcel only needs a courier to complete, and once parcels in $\Psi _ { c }$ and $\Gamma _ { c }$ are assigned to the courier $c ,$ they cannot be changed. 

Following the existing works [21], [22], [23], [47], we insert the new location of pick-up parcel $\tau$ into the optimal position in $L _ { c }$ by minimizing the total travel distance, without causing any reordering. As discussed in [19], [21], reordering all scheduled locations significantly increases computational overhead, making it unsuitable for real-time scenarios where parcel insertion operations are invoked frequently. 

# 2.2 Auction Model

The auction model is a typical incentive mechanism that effectively motivates participants to actively and truthfully compete for items [15], [17], [21], [34], [39]. Traditional auction models primarily rely on a single-layer auction [17], [21] to find the best courier for each parcel. However, in our system model, the local platform cooperates with other platforms to improve the quality of parcel assignment. To this end, exploring how to bid among platforms and their couriers is a key issue. Hence, we introduce our auction model, i.e., DLAM, which aims to find the best assignments between parcels and cross couriers through a double-layer auction process: 

• In the first layer, the DLAM employs a First-Price Sealed Auction (FPSA) among cross-platform couriers, where bidders are cross-platform couriers and the highest bidder wins the assignment. 

• In the second layer, the DLAM leverages the Reverse Vickrey Auction (RVA) among cooperating platforms, where bidders are cooperating platforms, and the lowest bidder wins but pays the second-lowest bid price among platforms. 

Compared to single-layer auction models [21], [17], DLAM considers the true bids of cooperating platforms and their couriers, ensuring the revenues of all three involved parties, i.e., the platform, cooperating platforms, and couriers. In what follows, we detail the FPSA and RVA. 

In the FPSA, to avoid cross couriers maliciously bid, we calculate the courier’s bid based on the courier’s preference for pick-up parcels, in which the platform could control the upper bound of the bidding price. Specifically, given a cooperating platform $P _ { - }$ , each belonged courier $c _ { P } ^ { i }$ determines his/her optimal bid $B _ { F } ( c _ { P } ^ { i } , \tau )$ in terms of detour ratio $\Delta d _ { \tau }$ , and performance $g ( c _ { P } ^ { i } )$ in historical parcel services, which is calculated as follows: 

$$
B _ {F} \left(c _ {P} ^ {i}, \tau\right) = p _ {\min } + \left(\alpha_ {c _ {P} ^ {i}} \cdot \Delta d _ {\tau} + \beta_ {c _ {P} ^ {i}} \cdot g \left(c _ {P} ^ {i}\right)\right) \gamma p _ {\tau} ^ {\prime}, \tag {1}
$$

where $\gamma$ denotes the sharing rate of the cooperating platform $P , \ p _ { \mathrm { m i n } }$ is the basic price satisfying $p _ { m i n } ~ \leq ~ ( 1 ^ { { \bar { ~ } } } - \gamma ) p _ { \tau } ^ { \prime } ,$ $\alpha _ { c _ { P } ^ { i } }$ and $\beta _ { c _ { P } ^ { i } }$ are two preference coefficients to balance the effect of $\Delta d _ { \tau }$ and $g ( c _ { P } ^ { i } ) .$ , and $p _ { \tau } ^ { \prime }$ is the maximum payment that $P$ is willing to offer its couriers with respect to $\tau$ . For simplicity, we set $p _ { \tau } ^ { \prime } = \mu _ { 1 } p _ { \tau } ,$ where $\mu _ { 1 }$ is the sharing rate of Loc. The detour ratio is calculated by τ 1<k≤|Lc|−1   d(lk,lτ )+d(lτ ,lkcalculated by g(ciP ) = 13N PNj=1(QSjciP where $\begin{array} { r } { \Delta d _ { \tau } \ = \ \mathrm { m i n } _ { 1 < k \le | L _ { c } | - 1 } 1 \ - \ \frac { d ( l _ { k } , l _ { k + 1 } ) } { d ( l _ { k } , l _ { \tau } ) + d ( l _ { \tau } , l _ { k + 1 } ) } } \end{array}$ $N$ indicates the total number of historical delivery $\begin{array} { r } { g ( c _ { P } ^ { i } ) = \frac { 1 } { 3 N } \sum _ { j = 1 } ^ { N } ( Q S _ { c _ { P _ { - } } ^ { i } } ^ { j } + E S _ { c _ { P } ^ { i } } ^ { j } + C S _ { c _ { P } ^ { i } } ^ { j } ) . } \end{array}$ c iP $g ( c _ { P } ^ { i } )$ P parcels, $Q S _ { c _ { P } ^ { i } } ^ { j }$ c P is quality score, $E S _ { c _ { P } ^ { i } } ^ { j }$ c iP is efficiency score, and $C S _ { c _ { P } ^ { i } } ^ { j }$ is customer satisfaction score. These three values of attributes are evaluated by historical data and mapped to a range of 0-1. It is important to note that each courier $c _ { P } ^ { i }$ bids based on their independent evaluation of the parcel, without knowledge of the bids from other bidders. To this end, the cooperating platforms could control the payment through $P _ { m i n }$ and $\gamma$ to ensure their revenue. After each available courier $c _ { P } ^ { i }$ offers the bid $B _ { F } ( c _ { P } ^ { i } , \tau )$ for the parcel $\tau _ { \iota }$ , the cooperating platform selects the highest-bid courier $c _ { P } ^ { i }$ as the winner, and their bid is considered to be the winning price, i.e., 

$$
p ^ {\prime} (\tau , c _ {w i n} ^ {P}) = \max  \left\{B _ {F} \left(c _ {P} ^ {i}, \tau\right) \mid c _ {P} ^ {i} \in C _ {P} \right\}. \tag {2}
$$

In the RVA, each cooperating platform $P$ uses the highest bid $p ^ { \prime } ( \tau , c _ { w i n } ^ { P } )$ in the first-layer auction as the starting price of the second-layer auction. Given a pick-up parcel $\tau _ { \iota }$ , and $k$ candidate cooperating platforms $\mathcal { P } _ { \tau } = \{ \bar { P } _ { 1 } , \cdot \cdot \cdot , P _ { k } \} ,$ , the bid for each cooperating platform $P \in \mathcal { P } _ { \tau }$ is determined by considering two key factors: the starting bid $p ^ { \prime } ( \tau , c _ { w i n } ^ { P } )$ , and the cooperation quality $f ( P )$ with the local platform Loc. Based on these considerations, the bidding function $B _ { R } ( P , \tau )$ is defined as follows, 

$$
B _ {R} (P, \tau) = \left\{ \begin{array}{l l} p ^ {\prime} \left(\tau , c _ {w i n} ^ {P}\right) + \mu_ {2} p _ {\tau} & \text {i f} | \mathcal {P} _ {\tau} | = 1 \\ p ^ {\prime} \left(\tau , c _ {w i n} ^ {P}\right) + f (P) \mu_ {2} p _ {\tau} & \text {i f} | \mathcal {P} _ {\tau} | \geq 2 \end{array} , \right. \tag {3}
$$

where $\mu _ { 2 }$ is a sharing rate of Loc satisfying $\mu _ { 1 } + \mu _ { 2 } \leq 1 \quad$ , and cooperation quality satisfies $f ( P ) \leq 1$ . As for Eq. 3, when there is a single bidder, i.e., $\begin{array} { r } { | \mathcal { P } _ { \tau } | = 1 , } \end{array}$ the payment reaches the maximum value. For the common case where $| \mathcal { P } _ { \tau } | \geq 2 ,$ the bid $B _ { R } ( P , \tau )$ of $P$ is guaranteed by $p ^ { \prime } ( \tau , c _ { w i n } ^ { P } )$ , and could obtain an additional reward by considering cooperation quality $\begin{array} { r } { f ( P ) \ = \ \frac { \overline { Q } _ { P } ^ { L o c } } { T _ { L o c } } . } \end{array}$ QLP where $\overline { { Q } } _ { P } ^ { L o c }$ QP represents the average historical cooperation quality between $P$ and Loc calculated by the average performance $g ( c _ { P } ^ { i } )$ of all cross couriers, and $T _ { L o c }$ denotes the historical maximum cooperation quality between all cooperating platforms and the local platform. In RVA, the cooperating platform $P$ with the lowest bid is selected as the winner $P _ { w i n } ,$ and the second-lowest bid among all bids $p _ { \tau } ^ { \prime } ( \tau , P _ { w i n } )$ is considered as the final payment to $P _ { w i n }$ , i.e., 

$$
p ^ {\prime} (\tau , P _ {w i n}) = \min  \left\{B _ {R} (P, \tau) | P \in \left(\mathcal {P} \backslash P _ {w i n}\right) \right\}. \tag {4}
$$

We clarify that $p ^ { \prime } ( \tau , c _ { w i n } ^ { P } )$ is the payment to the winner courier $c _ { w i n } ^ { P }$ winin the first-layer auction, and $p ^ { \prime } ( \tau , P _ { w i n } )$ is the payment to the winner cooperating platform $P _ { w i n }$ in the second-layer auction. Moreover, to enhance clarity, we use $p ^ { \prime } ( \tau , c ^ { P _ { w i n } } )$ to represent the final payment for the parcelcourier assignment, which corresponds to $p ^ { \prime } ( \tau , P _ { w i n } )$ . Note 

that the double-layer auctions discussed in this paper are conducted under sealed-bid conditions, which means that couriers and platforms only need to provide their own preference attributes without knowledge of the bids submitted by others [8], [29], [34]. To further exemplify the operation of DLMA, we give a toy example as follows. 

Example 2. Suppose that there are a pick-up parcel $\tau$ of the local platform Loc with a fare $p _ { \tau }$ and two cooperative platforms $P _ { 1 } , P _ { 2 }$ . In the FPSA, the workers in the two independent platforms auction with the highest sealed policy. Assuming that winner bidding prices are $B _ { F } ( c _ { P _ { 1 } } ^ { i } , \tau ) = 2 . 5$ and $B _ { F } ( c _ { P _ { 2 } } ^ { j } , \tau ) = 3 . 5$ respectively. Next, based on $B _ { F } ( c _ { P _ { 1 } } ^ { i } , \tau )$ and $B _ { F } ( c _ { P _ { 2 } } ^ { j } , \tau )$ , in the RVA, $P _ { 1 }$ and $P _ { 2 }$ give bids of $B _ { R } ^ { \ i } ( P _ { 1 } , \tau ) = 2 . 8$ and $B _ { R } ( P _ { 2 } , \tau ) = 3 . 7 ,$ respectively. According to the policy of RVA, the cross-platform winner is $P _ { 1 }$ with the payment 3.7. 

# 2.3 Problem Formulation

Based on the system and auction models above, in this section, we formally introduce the revenue of the local platform and the definition of the CPUL problem. 

Definition 4 (Revenue). Given a pick-up parcel $\tau ,$ when the parcel $\tau$ is completed by an inner courier $c _ { i } ,$ the revenue of the local platform is $p _ { \tau } - R c ( \tau , c _ { i } )$ , where $R c ( \cdot , \cdot )$ denotes the payment for $c _ { i } ;$ when $\tau$ is performed by a courier $c _ { j }$ from cooperating platform $P$ , the revenue of the local platform is $p _ { \tau } - \dot { p ^ { \prime } } ( \tau , c _ { j } ) ,$ , where $p ^ { \prime }$ denotes the payment for $P$ . 

Simply put, we calculate $R c ( \tau , c )$ of the matching pair $( \tau , c )$ with a fixed fare $R c ( \tau , c ) ~ = ~ \zeta \cdot p _ { \tau } ,$ , where $\zeta$ is an adjustable parameter. To simplify the problem setting, we assume that the local platform does not participate in the cross-platform parcel assignments of other platforms. Accordingly, the platform’s revenue is primarily derived from the successful completion of inner pick-up parcels. To this end, we formally define the CPUL problem. 

Definition 5 (CPUL Problem). Given a set of pick-up parcels $\Gamma _ { L } ,$ a set of inner couriers $C _ { L }$ and a set of cooperative platforms $\mathcal { P }$ with cross couriers $C _ { \mathcal { P } }$ , the CPUL problem aims to find the best parcel assignment that maximizes the overall revenue of the local platform, which is formulated as 

$$
\begin{array}{l} \operatorname {R e v} _ {S} \left(\Gamma_ {L}, C _ {L}, \mathcal {P}\right) = \sum_ {\left(\tau_ {i}, c _ {i}\right) \in \Gamma_ {L} \times C _ {L}} \left(p _ {\tau_ {i}} - R c \left(\tau_ {i}, c _ {i}\right)\right) \tag {5} \\ + \sum_ {(\tau_ {j}, c _ {j}) \in \Gamma_ {L} \times C _ {\mathcal {P}}} \\ \end{array}
$$

In what follows, we theoretically analyze the hardness of the CPUL problem in Theorem 1. 

# Theorem 1. The CPUL problem is NP-hard.

Proof. We prove the hardness of the CPUL problem by simplifying it to a known NP-hard problem, i.e., the 0-1 knapsack problem. In the 0-1 knapsack problem, given a set of items $R ,$ where each item $r _ { i } \in R$ has a specific weight $z _ { i } ,$ value $p _ { i } ,$ and a knapsack of limited capacity (maximum capacity $W$ ), the goal is to select a subset of items $R _ { 1 } \subseteq R$ to put in the knapsack to maximize the total value of the items in the knapsack $\sum _ { r _ { i } \in R _ { 1 } } p _ { i } ,$ while ensuring the total weight of the selected items satisfies $\textstyle \sum _ { r _ { i } \in R _ { 1 } } w _ { i } \leq W$ . 

In the CPUL problem, we can construct a similar instance and map it to the 0-1 knapsack problem. Specifically, in the 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/d0a1247146de559a82e6da62e73d0e56a432c477cc08d438317de17b45cffb40.jpg)



Fig. 3. The pipeline of the CAPA framework.


CPUL problem, the drop-off parcel set satisfies $\Psi = \emptyset$ and the pick-up parcel set Γ (corresponding to the item set $R$ in the 0-1 knapsack problem) contains a series of parcels, where each is associated with either a local courier or a crossplatform courier (assuming each courier can handle one parcel, and there are enough couriers). The value $p _ { i }$ of each parcel $\tau _ { i }$ depends on the factors related to the completion of the parcel and the type of courier, similar to the value $h _ { i }$ (a constant) in the 0-1 knapsack problem, hence this variation does not reduce the complexity of the CPUL problem. Additionally, we set a set of couriers $C$ containing $n$ couriers, ensuring that the total number of couriers assigned to all tasks does not exceed $n$ . Thus, the CPUL problem has the same objective as the 0-1 knapsack problem, which is to determine a subset of parcels $\hat { \Gamma } ^ { ' } \subseteq \Gamma$ such that $\sum { } _ { \tau { } _ { i } \in \Gamma } p _ { i }$ is maximized, while satisfying $\begin{array} { r } { \sum _ { \tau \in \Gamma } w _ { \tau } \leq \sum _ { c \in C } \overline { { w } } _ { c } } \end{array}$ . In this way, we can effectively reduce the 0-1 knapsack problem to the CPUL problem. Since the 0-1 knapsack problem is known to be NP-hard, the CPUL problem is also NP-hard. Thus, the proof is completed. □ 

# 3 PROPOSED SOLUTION

In this section, we introduce the CAPA framework to address the CPUL problem and detail its main components. 

# 3.1 Framework Overview

As illustrated in Fig. 3, the CAPA framework optimizes parcel assignment by integrating local-platform and crossplatform collaboration. Specifically, as presented in Algorithm 1, given a stream of pick-up parcels $\Gamma$ and a set of couriers $C$ in the local platform Loc, a set of cooperating platforms $\mathcal { P }$ and a batch size threshold $\Delta b ,$ the local platform first perceives the real-time environment to obtain the dynamic status and distribution of parcels and couriers, and accumulates the parcel stream into sequential batches (lines 1-4). In each batch, parcels with matching utility values $u ( \tau , c )$ exceeding the dynamic threshold $T _ { h }$ are directly assigned to the corresponding couriers by the CAMA algorithm (line 6). Otherwise, parcels enter an auction pool to perform cross-platform parcel assignment (line 

Algorithm 1 Cross-Aware Parcel Assignment (CAPA) Framework Input: a stream of pick-up parcels $\Gamma$ and a set of couriers $\overline { { C } }$ in Loc, a set of cooperating platforms $\mathcal { P }$ and a batch size $\Delta b$ Output: a matching plan $\mathcal { M }$ 

1: $\mathcal { M }  \emptyset$ , $\Gamma _ { S }  \emptyset$ and $t _ { c u m } = 0$ 

2: while timeline $t$ is not terminal do 

3: Retrieve new arriving pick-up parcels $\Gamma _ { t }$ at $t$ from $\Gamma$ ; 

4: $\Gamma _ { S }  \Gamma _ { S } \cup \Gamma _ { t } ;$ 

5: if $t _ { c u m } = = \Delta b$ then 

6: Retrieve available inner couriers $C _ { S }$ from $C$ 

7: Retrieve available platforms $\mathcal { P } _ { S }$ from $\mathcal { P }$ 

8: $\mathcal { M } _ { l o } , \mathcal { L } _ { c r } $ call CAMA Algorithm $( \Gamma _ { S } , C _ { S } ) _ { . }$ 

9: $\mathcal { M } _ { c r } \gets$ call DAPA Algorithm $( \mathcal { P } _ { S } , \mathcal { L } _ { c r } )$ 

10: $\mathcal { M }  \mathcal { M } \cup \mathcal { M } _ { l o } \cup \mathcal { M } _ { c r } ;$ 

11: Mcr ← ∅, Mlo ← ∅, $\Gamma _ { t }  \emptyset$ and $t _ { c u m } = 0$ tcum = tcum + 1; 

12: return $\mathcal { M }$ ; 

7). Finally we summarize the matching plan derived from the CAMA and the CAPA (line 8). Specifically, for each parcel in the auction pool, the CAPA processes parcels as follows: $\textcircled{1}$ Couriers eligible for cross-platform assignment receive information about the parcels in the auction pool. $\textcircled{2}$ In each cross platform, couriers place bids according to FPSA algorithm, and then the optimal courier is preallocated. $\textcircled{3}$ The bidding between cross platforms is further conducted using the RVA algorithm. $\textcircled{4}$ The local platform confirms the final winner. $\textcircled{5}$ The local platform notifies the respective platform and its winning courier to complete the pick-up parcel. 

The CAPA framework integrates local-platform assignment and cross-platform assignment, ensuring parcel matching efficiency and service quality and achieving a winwin situation for all parties involved. In what follows, we detail all involved algorithms. 

# 3.2 Local-Platform Parcel Assignment

In the local-platform parcel assignment phase, we propose the CAMA algorithm to efficiently identify the optimal 


Algorithm 2 Cross-aware Matching Algorithm (CAMA)


Input: a set of pick-up parcels $\Gamma_t$ and inner couriers $C_S$ Output: the parcel assignment $\mathcal{M}_{lo}$ and an auction pool $\mathcal{L}_{cr}$ 1: $\mathcal{M}_{lo} \gets \emptyset$ , $\mathcal{L}_{cr} = \emptyset$ , $M_t \gets \emptyset$ and $\mathcal{G} \gets \emptyset$ ;  
2: for each parcel $\tau_i \in \Gamma_t$ do  
3: $\mathcal{S}_{\tau} \gets \emptyset$ ;  
4: for each courier $c_j \in C_S$ do  
5: if $c_j$ can reach $l_{\tau_i}$ before $t_{\tau_i}$ and $w_{\tau_i} \leq \overline{w}_{c_j}$ then  
6: Calculate utility $u(\tau_i, c_j)$ ;  
7: Insert $(\tau_i, c_j, u(\tau_i, c_j))$ into $\mathcal{S}_{\tau}$ ;  
8: if $|\mathcal{S}_{\tau}| \neq 0$ then  
9: $M_t \gets M_t \cup S_{\tau}$ ;  
10: $(\tau_i, c_j) \gets \arg \max_{(\tau_i, c_j) \in S_{\tau}} u(\tau_i, c_j)$ ;  
11: $\mathcal{G} \gets \mathcal{G} \cup \{(\tau_i, c_j, u(\tau_i, c_j))\}$ ;  
12: else  
13: $\mathcal{L}_{cr} \gets \mathcal{L}_{cr} \cup \{\tau_i\}$ ;  
14: Invoke Eq. 7 to calculate threshold $T_h$ based on $M_t$ ;  
15: for each $(\tau_i, c_j, u(\tau_i, c_j)) \in \mathcal{G}$ do  
16: if $u(\tau_i, c_j) \geq T_h$ then  
17: $\mathcal{M}_{lo} \gets \mathcal{M}_{lo} \cup \{(\tau_i, c_j)\}$ ;  
18: else  
19: $\mathcal{L}_{cr} \gets \mathcal{L}_{cr} \cup \{\tau_i\}$ ;  
20: return $\mathcal{M}_{lo}, \mathcal{L}_{cr}$ 

inner courier for each pick-up parcel in a batch manner. As illustrated in the yellow area of Fig. 3, CAMA initially adopts a quality-aware strategy to assign each parcel to a suitable courier, with the objective of maximizing the local platform’s revenue. More specifically, a dynamic threshold is applied to categorize parcels as either high-quality or low-quality. High-quality parcels are directly matched with the optimal local couriers, while low-quality parcels are deferred to the auction pool for potential cross-platform assignment. The parcels that are not allocated in the current batch (i.e., neither matching in the current local-platform assignment nor cross-platform assignment) will reenter the next batch for re-matching. 

To evaluate the quality of a potential matching pair $( \tau , c )$ between a parcel $\tau$ and an inner courier $c ,$ we introduce a utility-aware evaluator $u ( \tau , c )$ that jointly considers the parcel’s weight (or capacity) and detour distance incurred by the courier. Intuitively, the local platform prioritizes assigning parcels to couriers with greater remaining capacity and minimal detour distance. As such, the utility $u ( \bar { \tau } , c )$ is computed as follows: 

$$
u (\tau , c) = \gamma \cdot \Delta w _ {\tau} + (1 - \gamma) \cdot \Delta d _ {\tau}, \tag {6}
$$

where ∆w = 1 − Pψ∈Ψc wψ+Pτ∈Γc wτ $\begin{array} { r } { \Delta w _ { \tau } = 1 - \frac { \sum _ { \psi \in \Psi _ { c } } w _ { \psi } + \sum _ { \tau \in \Gamma _ { c } } w _ { \tau } } { w _ { c } } } \end{array}$ wc upiedis the capacity ratio, ∆dτ = min1≤i≤|Sw|−1 π(li,li+1)π(li,lτ )+π(lτ ,li+1) $\begin{array} { r } { \Delta d _ { \tau } = \operatorname* { m i n } _ { 1 \leq i \leq | S _ { w } | - 1 } \frac { \pi ( l _ { i } , l _ { i + 1 } ) } { \pi ( l _ { i } , l _ { \tau } ) + \pi ( l _ { \tau } , l _ { i + 1 } ) } } \end{array}$ detour ratio, and $\gamma$ is a balance coefficient. To distinguish high-quality parcels, we also maintain a dynamic threshold $T _ { h } ,$ which is adaptively updated based on the average utility of all potential matching pairs $M _ { t } ,$ i.e., 

$$
T _ {h} = \omega \cdot \sum_ {\left(\tau_ {i}, c _ {j}\right) \in M _ {t}} u \left(\tau_ {i}, c _ {j}\right) / \left| M _ {t} \right|, \tag {7}
$$

where $\omega$ is a sensitivity adjustment factor and $M _ { t }$ records all potential matching pairs. 

Algorithm details. Algorithm 2 presents the pseudo-code of the CAMA algorithm, which is designed to efficiently assign pick-up parcels within the local platform Loc. Given 

a batch of pick-up parcels $\Gamma _ { t }$ and a set of local couriers $C _ { S }$ , CAMA first identifies all feasible courier-parcel pairs by verifying constraints such as arrival time and capacity (Lines 2–7). For each parcel with at least one feasible courier, the algorithm selects the courier yielding the highest utility and adds the corresponding pair to a candidate set $\mathcal { G }$ (Lines 8–11). If no feasible courier is found, the parcel is directly added to the auction pool $\mathcal { L } _ { c r }$ for potential cross-platform assignment(Line 13). Subsequently, a dynamic utility threshold $T _ { h }$ is computed based on the average utility of all candidate pairs (Line 14). Based on this threshold, the algorithm assigns high-utility pairs (i.e., those satisfying $u ( \tau , c ) \geq T _ { h } )$ to form the local parcel assignment $\mathcal { M } _ { l o } ,$ while putting the remaining parcels into the auction pool $\mathcal { L } _ { c r }$ for further processing (Lines 15–19). The algorithm outputs both the finalized local assignments $\mathcal { M } _ { l o }$ and the updated auction pool $\mathcal { L } _ { c r }$ (Line 20). 

Complexity Analysis. The time complexity of the CAMA algorithm is $O ( n m )$ , where $n , ~ m$ represent the number of parcels and inner couriers, respectively. 

# 3.3 Cross-Platform Parcel Assignment

When local-platform parcels cannot be effectively served by inner couriers, as depicted in the green area of Fig. 3, they are collected to an auction pool $\mathcal { L } _ { c r }$ for cross-platform assignment, and further processed by the DAPA algorithm. The DAPA algorithm operates through two hierarchical auction layers. In the first layer, each participating platform conducts FPSA internally, allowing its couriers to bid competitively for cross parcels. In the second layer, RVA is employed across cooperating platforms to determine the winning platform based on the most cost-effective bids. 

In the DAPA algorithm, parcel information in the auction pool, such as weight and location, is initially broadcast to all cooperating platforms, which in turn repeat it to their affiliated couriers. In the first-layer FPSA, each cooperating platform independently conducts internal auctions among its couriers. Couriers evaluate the bids for parcels based on their current status and submit sealed bids $B _ { F } ( c _ { P } ^ { i } , \tau )$ for desirable parcels. The courier with the highest bid wins the parcel, and the winning bid becomes the final transaction price. The winning couriers from each platform are then passed to the second-layer inter-platform auction for crossplatform selection. We give a running example to illustrate the operation of FPSA. 

Example 3. As illustrated in pipeline $\textcircled{1}$ of Fig. 4, consider a parcel with a weight of 0.8 (i.e., subject to a capacity constraint) and a fare of 10. The sharing rates at the two-level auction stages are set as $\mu _ { 1 } ~ = ~ 0 . 5$ and $\mu _ { 2 } ~ = ~ 0 . 4$ . Hence, the maximum price $P _ { l i m } ( \tau )$ that the local platform Loc is willing to pay to a cooperating platform is 9.0, while the maximum fare allocated for the first-tier FPSA stage is 5.0. Assume that three couriers from platform $P _ { 1 }$ submit the following bids: $B _ { F } ( c _ { P _ { 1 } } ^ { 1 } , \tau ) ~ =$ 3.62, $B _ { F } ( c _ { P _ { 1 } } ^ { 2 } , \tau ) ~ = ~ 3 . 6 6 ,$ and $B _ { F } ( c _ { P _ { 1 } } ^ { 3 } , \tau ) ~ = ~ 3 . 8 \dot { 0 }$ . Since $B _ { F } ( c _ { P _ { 1 } } ^ { 3 } , \tau ) ~ \stackrel { . } { > } ~ B _ { F } ( c _ { P _ { 1 } } ^ { 2 } , \tau ) ~ > ~ B _ { F } ( c _ { P _ { 1 } } ^ { 1 } , \stackrel { . } { \tau } ) ,$ courier $c _ { P _ { 1 } } ^ { 3 }$ is declared the winner on platform auctions of other cooperatin $P _ { 1 }$ . Similarly, in the iplatforms, courier nal FPSAwins on $c _ { P _ { 2 } } ^ { 3 }$ platform $P _ { 2 }$ with a bid of 5.54, and courier $c _ { P _ { 3 } } ^ { 2 }$ wins on platform $P _ { 3 }$ with a bid of 3.26. 

The second-layer auction RVA is conducted among cooperating platforms to determine the winning platform based 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/86edadb3747f9d6b1180c523712406f70a6723a97ebe604d2ffd75020eba47a0.jpg)



Fig. 4. A toy example of the DAPA algorithm.


on the winning bid of the first-tier FPSA. In the RVA, the platform offering the lowest bid is selected as the winner, but is paid using the second-lowest bid. The payment is executed only if it does not exceed the upper limit predefined payment $\dot { P } _ { l i m } ( \tau )$ by the local platform, thereby ensuring that inter-platform cooperation remains both cost-effective and mutually beneficial. 

Example 4. As illustrated in pipeline $\textcircled{2}$ of Fig. 4, the local platform selects the platform that submits the lowest bid, while the final payment is set to the second-lowest bid. The numbers in parentheses beside each cooperating platform represent their average historical collaboration quality scores. Specifically, for parcel $\tau ,$ platforms $P _ { 1 }$ , $P _ { 2 } ,$ and $P _ { 3 }$ submit bids of 5.59, 9.29, and 5.75, respectively. The bid ranking satisfies the order $B _ { R } ( P _ { 1 } , \tau ) < B _ { R } ( \dot { P } _ { 3 } , \tau ) \dot { < } P _ { l i m } ( \tau ) < B _ { R } ( \dot { P } _ { 2 } , \tau ) .$ , where the bid from $P _ { 2 }$ exceeds the upper payment limit $P _ { l i m } ( \tau ) = 9 . 0 $ set by the local platform. As such, $P _ { 2 }$ is disqualified, and $P _ { 1 }$ is selected as the winning platform. According to the RVA mechanism, $P _ { 1 }$ is paid the second-lowest bid, i.e., 5.75. Platform $P _ { 1 }$ then assigns the parcel to its winning courier $c _ { P _ { 1 } } ^ { 3 }$ , who previously bid 3.8 during the FPSA stage. As a result, the revenue of platform $P _ { 1 }$ is1.95; the revenue of the local platform Loc is 4.25. 

Algorithm details. The pseudo-code of the DAPA algorithm is presented in Algorithm 3, which allocates parcels in the auction pool to cross couriers via a dual-layer auction mechanism. For each parcel $\tau _ { i } ,$ DAPA first performs FPSA in each cooperating platform (Lines 4–15). Specifically, for each cooperating platform $P _ { j } ,$ it identifies all available couriers and evaluates the feasibility of assigning parcel $\tau _ { i }$ to each courier based on predefined constraints. If a match is valid, the courier submits a sealed bid $B _ { F } ( c _ { P _ { j } } ^ { k } , \tau _ { i } )$ according to Eq. 1, and all valid bids are collected into the set $\boldsymbol { B } _ { F }$ (Lines 7–11). If $\boldsymbol { B } _ { F }$ is non-empty, the courier with the highest bid is selected as the internal winner for $\tau _ { i } ,$ and the bid is added to the inter-platform bid set $B _ { \tau _ { i } }$ (Lines 12–15). The DAPA then proceeds to RVA (Lines 17–28). If at least two cooperating platforms have submitted bids (i.e., $| B _ { \tau _ { i } } | \geq 2 )$ ), platform-level bids $B _ { R } ( P _ { j } , \tau _ { i } )$ are computed based on Eq. 3 and stored in $\scriptstyle { B _ { R } }$ . The platform offering the lowest bid is selected as the winner, while the final transaction price is set 

Algorithm 3 Dual-layer Auction-based Parcel Assignment (DAPA) 

Input: a set of cross parcels $\mathcal { L } _ { c r }$ and cross platforms $\mathcal { P } _ { S }$ 

Output: a courier-parcel assignment $\mathcal { M } _ { c r }$ 

$$
\begin{array}{l} 1: \mathcal {M} _ {c r} \leftarrow \phi ; \\ 3: \quad / ^ {*} \quad \text {S t e p 1 : T h e F P S A p r o c e s s} \quad * / \\ 4: \quad \mathcal {B} _ {\tau_ {i}} \leftarrow \emptyset ; \\ 6: \quad \mathcal {B} _ {F} \leftarrow \emptyset ; \\ 7: \quad C _ {P _ {i}} \leftarrow \text {O b t a i n} P _ {i}; \\ 8: \quad \text {f o r e a c h c o u r i e r} c _ {P _ {j}} ^ {k} \in C _ {P _ {j}} \mathbf {d o} \\ 9: \quad \text {i f} \left(c _ {P _ {j}} ^ {k}, \tau_ {i}\right) \text {i s v a l d t h e n} \\ \text {I n v o k e E q . 1 t o c a l c u l a t e} B _ {F} \left(c _ {P _ {i}} ^ {k}, \tau_ {i}\right); \\ 1 1: \quad \mathcal {B} _ {F} \leftarrow \mathcal {B} _ {F} \bigcup \left\{\left(\tau_ {i}, c _ {P _ {j}} ^ {k}, P _ {j}, B _ {F} \left(c _ {P _ {j}} ^ {k}, \tau_ {i}\right)\right) \right\}; \\ 1 2: \quad \text {i f} \mathcal {B} _ {F} \text {i s n o t e m p t y t h e n} \\ \text {S o r t} \mathcal {B} _ {F} \text {i n} \text {d e s c e n d i n g} B _ {F} \left(c _ {P _ {j}} ^ {k}, \tau_ {i}\right); \\ \left(\tau_ {i}, c _ {P _ {i}} ^ {k}, P _ {j}\right) \leftarrow \text {t h e f i r s t} \mathcal {B} _ {F}; \\ \mathcal {B} _ {\tau_ {i}} \leftarrow \mathcal {B} _ {\tau_ {i}} \bigcup \left\{\left(c _ {P _ {j}} ^ {k}, \tau_ {i}, P _ {j}, B _ {F} \left(c _ {P _ {j}} ^ {k}, \tau_ {i}\right)\right) \right\}; \\ 1 6: \quad / * \quad \text {S t e p 2 : T h e R V A p r o c e s s} \quad * / \\ 1 7: \quad \text {i f} | \mathcal {B} _ {\tau_ {i}} | \geq 2 \text {t h e n} \\ 1 8: \quad \mathcal {B} _ {R} \leftarrow \emptyset ; \\ 1 9: \quad \text {f o r e a c h} \left(c _ {P _ {j}} ^ {k}, \tau_ {i}, P _ {j}\right) \in \mathcal {B} _ {\tau_ {i}} \mathbf {d o} \\ 2 0: \quad \text {I n v o k e} B _ {R} (P _ {j}, \tau_ {i}); \\ \mathcal {B} _ {R} \leftarrow \mathcal {B} _ {R} \bigcup \left\{\left(c _ {P _ {j}} ^ {k}, \tau_ {i}, P _ {j}, B _ {R} \left(P _ {j}, \tau_ {i}\right)\right) \right\}; \\ 2 2: \quad \text {S o r t} \mathcal {B} _ {R} \text {i n a s c e n d i n g o r d e r o f b i d s} B _ {R} \left(P _ {j}, \tau_ {i}\right); \\ 2 3: \quad \left(c _ {P _ {i}} ^ {k}, \tau_ {i}, P _ {j}\right) \leftarrow \text {t h e f i r s t t u p l e} \mathcal {B} _ {R}; \\ 2 4: \quad p ^ {\prime} \left(\tau_ {i}, P _ {w i n}\right) = \min  \left\{B _ {R} \left(P, \tau_ {i}\right) \mid P \in \left(\mathcal {B} _ {R} \backslash P _ {w i n}\right) \right\}; \\ 2 5: \quad \mathcal {M} _ {c r} \leftarrow \mathcal {M} _ {c r} \bigcup \left\{\left(\tau_ {i}, c _ {P _ {w i n}} ^ {\prime}\right) \right\}; \\ 2 6: \quad \text {i f} | \mathcal {B} _ {\tau_ {i}} | = = 1 \text {t h e n} \\ 2 7: \quad p ^ {\prime} (\tau_ {i}, P _ {w i n}) = B _ {F} \left(c _ {P _ {w i n}} ^ {k}, \tau_ {i}\right) + \mu_ {2} p _ {\tau}; \\ 2 8: \quad \mathcal {M} _ {c r} \leftarrow \mathcal {M} _ {c r} \bigcup \left\{\left(\tau_ {i}, c _ {P _ {w i n}} ^ {k}\right) \right\}; \\ 2 9: \text {r e t u r n} \mathcal {M} _ {c r} \\ \end{array}
$$

to the second-lowest bid to promote truthful bidding (Lines 22–24). The resulting assignment is recorded in the matching set $\mathcal { M } _ { c r }$ (Line 25). If only one platform participates, the winner is assigned by default, and the transaction price is set to the maximum allowed value defined by Eq. 3 (Lines 27–28). After all parcels have been processed, the algorithm returns the final cross-platform courier-parcel assignment set $\mathcal { M } _ { c r }$ (Line 29). 

Complexity Analysis. The time complexity of the DAPA algorithm is $O ( n m p \log m + n p \log p )$ , where $n , m ,$ and $p$ are the number of parcels, couriers per platform, and cooperating platforms, respectively. The FPSA process contributes $O ( n m p \log m )$ , and the RVA process adds $O ( n p \log p )$ . 

Discussion. The DAPA algorithm employs an efficient duallayer auction structure that not only incentivizes truthful bidding among participants, including both cooperating platforms and their couriers, but also guarantees individual rationality and profitability. Furthermore, the algorithm is efficiently computed as supported by complexity analysis. In the following, we provide a theoretical analysis and formal proof that the DLAM auction model implemented by DAPA is effective, as stated in Theorem 2. 

Theorem 2. The DAPA algorithm possesses the four key attributes of the auction model: truthfulness, individual rationality, 

# profitability, and computational efficiency.

Proof. We detail the proof of four attributes as follows: 

Computational efficiency. As shown in the complexity analysis above, the DAPA algorithm exhibits a polynomial time complexity of $O ( n m p \log m + n p \log p )$ , and therefore ensures computational efficiency. 

Profitability. The objective of the CPUL problem is to maximize the revenue of the local platform. For crossplatform parcels, the platform’s revenue is defined as $\mathbf { \tilde { \mathit { R e v } } } _ { c } = \mathbf { \tilde { \mathit { p } } } _ { \tau } \mathbf { \tilde { \Sigma } } - \mathbf { \mathit { p } } _ { \tau } ^ { \prime } ( \tau , c )$ (see Eq. (5)). Under the DLAM auction model, the payment $p _ { \tau } ^ { \prime } ( \tau , \bar { c } )$ to the winning cross-platform courier is deducted from the parcel fee $p _ { \tau }$ . Consequently, $R e v _ { c }$ is guaranteed to be non-negative, ensuring that the DAPA algorithm satisfies the profitability property for the local platform. Moreover, the profitability for other entities, namely, the cooperating platform and the cross-platform couriers, is also guaranteed. Specifically, the revenue of the cooperating platform is given by: $p _ { \tau } ^ { \prime } ( \bar { \tau } , P _ { \mathrm { w i n } } ) - p ^ { \prime } ( \tau , c _ { \mathrm { w i n } } ^ { P } )$ . According to the second-price bidding rule in the DLAM mechanism, the following inequality holds: $p _ { \tau } ^ { \prime } ( \tau , P _ { \mathrm { w i n } } ) \ -$ $\begin{array} { r } { p ^ { \prime } ( \tau , c _ { \mathrm { w i n } } ^ { P } ) ~ \geq ~ B _ { R } ( P , \tau ) ~ \smile ~ p ^ { \prime } ( \dot { \tau ^ { , } } c _ { \mathrm { w i n } } ^ { P } \dot { ) } ~ \geq ~ f ( \dot { P } ) \mu _ { 2 } p _ { \tau } ~ \geq ~ 0 } \end{array}$ . Therefore, the cooperating platform receives a non-negative profit. For the cross-platform couriers, the received payment satisfies $( 1 - \gamma ) p _ { \tau } ^ { \prime } \ \stackrel { \cdot } { \leq } \ p ^ { \prime } ( \tau , c _ { \mathrm { w i n } } ^ { P } ) \ \leq \ p _ { \tau } ^ { \prime } ,$ which clearly ensures profitability for the courier. In conclusion, the DAPA algorithm ensures non-negative revenues for all involved parties, the local platform, the cooperating platform, and the cross-platform couriers, thus satisfying the profitability requirement. 

Individual rationality. Following the definition and proof of individual rationality in prior work [21], if a parcel is profitable, then bidders, namely, the cooperating platforms and cross-platform couriers, are individually rational. The proof process for individual rationality closely aligns with the profitability analysis discussed above. For the cooperating platforms, their utility is given by: $p _ { \tau } ^ { \prime } ( \tau , P _ { \mathrm { w i n } } ) - p ^ { \prime } ( \dot { \tau _ { \mathrm { , } } } c _ { \mathrm { w i n } } ^ { P } ) \geq$ 0, which guarantees that their participation in the auction results in a non-negative gain. For the cross-platform couriers, the payment satisfies: $\breve { p ^ { \prime } } ( \tau , c _ { \mathrm { w i n } } ^ { P } ) > 0 .$ , indicating a positive reward upon winning the bid. Therefore, in accordance with the reasoning in [21], since all involved bidders obtain nonnegative profit, the DAPA mechanism satisfies the property of individual rationality. 

Truthfulness. To prove that the DLAM auction model is truthful, we show that for any bidder, either a cooperating platform or a cross courier, bidding truthfully is the best strategy. That is, no bidder can increase their expected revenue by giving false bids. We first analyze the truthfulness of cooperating platforms in the RVA layer. Consider a pick-up parcel $\tau$ and two cooperating platforms $P _ { 1 }$ and $P _ { 2 } ,$ , whose true bids are denoted by $\hat { B } _ { R } ( \tau , P _ { 1 } )$ and $B _ { R } ( \tau , P _ { 2 } )$ , respectively. In a sealed-bid second-price auction: If $B _ { R } ( \tau , \dot { P _ { 1 } } ) > \dot { B _ { R } } ( \tau , P _ { 2 } )$ , platform $P _ { 2 }$ wins the bid and pays $p _ { \tau } ^ { \prime } ( \tau , P _ { 2 } ) = B _ { R } ( \tau , P _ { 1 } )$ . Otherwise, $P _ { 1 }$ wins and pays $p _ { \tau } ^ { \prime } ( \tau , P _ { 1 } ) = B _ { R } ( \tau , P _ { 2 } )$ . Let the probabilities that $B _ { R } ( \bar { \tau } , P _ { 1 } ) ~ \leq ~ B _ { R } ( \tau , P _ { 2 } )$ and $\bar { B } _ { R } ( \tau , P _ { 1 } ) { \bf \bar { \tau } } > B _ { R } ( \tau , P _ { 2 } )$ be denoted by $P r _ { R } ( P _ { 1 } \leq P _ { 2 } )$ and $P r _ { R } ( P _ { 1 } > P _ { 2 } )$ , respectively. Then the expected incremental revenue of $P _ { 1 }$ under truthful bidding is: $\begin{array} { r } { \hat { \mathbb { E } } [ \Delta R e v ( \tau , P _ { 1 } ) ] = P r _ { R } ( P _ { 1 } \leq P _ { 2 } ) \cdot ( B _ { R } ( \tau , P _ { 2 } ) - } \end{array}$ $B _ { R } ( \tau , P _ { 1 } ) ) + P r _ { R } ( P _ { 1 } > P _ { 2 } ) \cdot 0$ . Now suppose $P _ { 1 }$ submits a false bid $B _ { R } ^ { \prime } ( \tau , P _ { 1 } ) > B _ { R } ( \tau , P _ { 1 } )$ . This reduces the probability of winning, i.e., $P r ^ { \prime } ( P _ { 1 } \leq P _ { 2 } ) < P r _ { R } ( P _ { 1 } \leq \hat { P } _ { 2 } )$ . If $B _ { R } ^ { \prime } ( \tau , P _ { 1 } ) > \bar { B } _ { R } ( \tau , P _ { 2 } ) ,$ P1 loses the auction with zero 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/9be345ec336066e3da5706cfee069675a6ab5506eeb877886284dbe8ef6eebfd.jpg)



Fig. 5. The pipeline of the RL-CAPA method.


revenue. If $B _ { R } ^ { \prime } ( \tau , P _ { 1 } ) \ < \ B _ { R } ( \tau , P _ { 2 } ) , \ F$ $P _ { 1 }$ still wins but receives the expected incremental revenue $\mathbb { E } [ \Delta R e v ^ { \prime } ( \tau , P _ { 1 } ) ] =$ $B _ { R } ( \tau , P _ { 2 } ) - \mathsf { \bar { B } } _ { R } ^ { \prime } ( \tau , P _ { 1 } ) < \mathbb { E } [ \Delta R e v ( \tau , P _ { 1 } ) ]$ . Therefore, misreporting yields a strictly lower or equal expected profit, and truthful bidding maximizes expected profit. Thus, cooperating platforms are incentivized to bid truthfully. Next, we analyze truthfulness for cross couriers in the FPSA layer. Consider a pick-up parcel $\tau$ and two cross couriers $c _ { 1 }$ and $c _ { 2 }$ from platform $P$ , with their respective bids denoted by $B _ { F } ( c _ { 1 } , \bar { \tau } )$ and $B _ { F } ( c _ { 2 } , \tau )$ . In the FPSA layer, the courier with the highest bid wins the parcel and is paid their own bid. Specifically, if $B _ { F } ( c _ { 1 } , \tau ) \hat { \ } > \ B _ { F } ( c _ { 2 } , \tau ) ,$ , then $c _ { 1 }$ wins parcel $\tau$ and receives payment $p ^ { \prime } ( \tau , c _ { 1 } ) = B _ { F } ( c _ { 1 } , \tau )$ . Let $\mathrm { P r } _ { F } ( c _ { 1 } > c _ { 2 } )$ and $\mathrm { P r } _ { \hat { F } } ( \bar { c } _ { 1 } \leq c _ { 2 } )$ denote the probabilities that $c _ { 1 }$ wins or loses the auction, respectively. The expected payment received by $c _ { 1 }$ when bidding truthfully is thus $\tilde { \mathbb { E } } [ \bar { p } ^ { \prime } ( \tau , c _ { 1 } ) ] = P r _ { F } ( \bar { c _ { 1 } } \leq c _ { 2 } ) \cdot B _ { F } ( c _ { 1 } , \tau ) \bar { + } 0 \cdot B _ { F } ( \bar { c _ { 1 } } , \tau )$ . Suppose now that $c _ { 1 }$ submits a false bid $B _ { F } ^ { \prime } ( c _ { 1 } , \tau ) < B _ { F } ( c _ { 1 } , \bar { \tau } )$ . In a sealed-bid auction, the bidder has no knowledge of the competitor’s bid, and lowering their bid decreases the probability of winning the parcel. That is, $P r _ { F } ^ { \prime } ( c _ { 1 } > c _ { 2 } ) <$ $\mathsf { \bar { P } } r _ { F } ( c _ { 1 } > c _ { 2 } )$ . Therefore, under the false bid, the expected payment becomes $\begin{array} { r } { \mathbb { E } [ p ^ { \prime } ( \tau , c _ { 1 } ) ] = P r _ { F } ^ { \prime } ( c _ { 1 } \leq c _ { 2 } ) \cdot B _ { F } ^ { \prime } ( \dot { c _ { 1 } } , \tau ) < } \end{array}$ ${ \overline { { P r } } } _ { F } ( c _ { 1 } ~ \le ~ c _ { 2 } ) ~ \cdot ~ B _ { F } ( c _ { 1 } , \tau ) .$ , which is strictly less than the expected payment under truthful bidding. Consequently, misreporting leads to a reduced chance of winning and a lower expected revenue, i.e., the best bidding strategy for each courier is to bid truthfully. 

Thus, the proof is completed. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/39014dee2bd674750bac1e0e135b9ea190e515d8ac3eda69a9944a6ecf98184b.jpg)


# 3.4 Dual-Stage Adaptive Assignment Optimization

Although the CAMA, a heuristic method, can effectively address the CPUL problem, it often falls into the local optimum in real-time parcel assignment, due to the lack of consideration of long-term rewards. Besides, real-time parcel assignment is inherently complex and dynamic, involving multiple factors such as parcel deadlines and courier capacity. Traditional methods, such as CAMA, are often limited in their ability to account for long-term rewards. In contrast, reinforcement learning (RL) offers significant advantages by dynamically adjusting decisions based on 

long-term rewards, adapting to changing environments, and learning optimal strategies over time. We hence introduce the RL-based method to address the CPUL problem. 

We observe a non-uniform distribution of parcels in the time dimension. For example, batches during peak hours may contain excessive pick-up parcels, while idle periods see sparse arrivals. Parcel assignment within fixed time batch sizes [21], [45] or fixed numbers of percels [31] encounters challenges in adapting to dynamic adjustment of the number of parcels. Recent studies [22], [37] have theoretically proven that if the in-batch matching algorithm yields a local optimum, e.g., via the KM algorithm [16], then there exists an adaptive batch-based strategy that guarantees the overall performance. Besides, each inner-platform parcel faces a binary decision: staying on the kocal platform or being assigned to cross platforms. Different actions bring different rewards, which also have dynamic properties and long-term effects. To this end, we propose the RL-CAPA, a dual-stage adaptive assignment method, as illustrated in Fig. 5. RL-CAPA dynamically adjusts the time batch size to improve efficiency, and adaptively determines a series of cross-or-not decisions of inner parcels within each time batch, i.e., either moving to the next batch or the auction pool. These two processes are mutually influential and work in tandem to address the CPUL problem effectively. We first formulate the batch size partitioning as a Markov Decision Process (MDP) $M _ { b } = ( S _ { b } , A _ { b } , P _ { b } , R _ { b } )$ : 

• Action Space $A _ { b }$ . The local platform is modeled as an agent that observes the environment and selects a batch size from the from the discrete action space $A _ { b } \ = \ [ h _ { L } , h _ { L + 1 } , \cdot \cdot \cdot , h _ { M } ] ,$ where $h _ { L }$ and $h _ { M }$ denote the minimum and maximum allowable batch sizes, respectively. Each action $a _ { t } \in A _ { b }$ represents a specific batch duration. For example, if $h _ { L } = 1 0$ and $h _ { M } = 2 0 .$ , the local platform can choose any of the 11 discrete batch durations (i.e., $a _ { t } \in \{ 1 0 , 1 1 , . . . , 2 0 \} )$ . In this case, an action $a _ { t } = 1 2$ would represent selecting a 12-second batch duration. 

• States Space $S _ { b }$ . The state $s _ { t } ~ \in ~ S _ { b }$ observed at time step t is represented by the feature vector $s _ { t } =$ $( | \dot { \Gamma _ { t } ^ { L o c } } | , | C _ { t } ^ { L o \dot { c } } | , | D | , | T | ) ,$ , where $| \Gamma _ { t } ^ { L o c } |$ and $| C _ { t } ^ { L o c } |$ denote the number of pending parcels and available couriers on the local platform, respectively. $| D |$ captures the average distance between couriers and pick-up tasks (lower values imply closer proximity), while $| T |$ quantifies task urgency relative to the current time slice and task deadline [22]. 

• Transition Probability $P _ { b } : S _ { b } \times A _ { b } \times S _ { b } \to [ 0 , 1 ]$ . It defines the probability distribution $\textstyle P _ { b } ( s _ { t + 1 } | s _ { t } , a _ { t } )$ of transitioning to the next state $s _ { t + 1 }$ given the current state $s _ { t }$ and selected batch size $a _ { t }$ . 

• Reward Function $R _ { b } : S _ { b } \times A _ { b }  \mathbb { R }$ . Given a transition from state $s _ { t }$ to $s _ { t + 1 }$ via action $\scriptstyle a _ { t } ,$ , the agent receives an immediate reward $\mathscr { R } ( s _ { t + 1 } \vert s _ { t } , a _ { t } )$ , defined as the total matching revenue $R e v _ { S } ( \Gamma _ { L o c } , C _ { L o c } , \mathcal { P } )$ obtained in the batch (see Eq. 5). The expected cumulative reward is computed as: 

$$
\mathbb {E} = \sum_ {t = 0} ^ {\infty} \gamma^ {t} R e v _ {S} ^ {t} (\Gamma_ {L o c}, C _ {L o c}, \mathcal {P}),
$$

where $\gamma ~ \in ~ [ 0 , 1 ]$ is a discount factor reflecting the importance of future versus immediate revenues. 

After determining the batch size, RL-CAPA enters the second stage. We formulate the decision of whether unassigned parcels should enter the auction pool or defer to the next batch as a Markov Decision Process (MDP) $M _ { m } =$ $( S _ { m } , A _ { m } , P _ { m } , R _ { m } )$ . The key components of $M _ { m }$ are defined as follows: 

• Action space $A _ { m }$ . In $M _ { m } ,$ each parcel is treated as an agent making the cross-or-not decision. Action $a _ { m } = 1$ assigns the parcel to the cross-platform auction pool, while $a _ { m } = 0$ defers it to the next batch. 

• States space $S _ { m }$ . Each state $s _ { m } \in S _ { m }$ is a feature vector $s _ { m } = ( | \Delta \Gamma | , t _ { \tau } , t _ { c u r } , \Delta b )$ , where $| \Delta \Gamma |$ is the number of unassigned parcels, $t _ { \tau }$ is parcel’s deadline $\tau \in \Delta \Gamma$ , $t _ { c u r }$ is the current time, and $\Delta b$ is the batch size from $M _ { b }$ . 

• Transition probability $P _ { m } : S _ { m } \times A _ { m } \times S _ { m } \to [ 0 , 1 ]$ . It models the transition probability $ { P } _ { m } ( s _ { m } ^ { \prime } \mid s _ { m } , a _ { m } )$ of moving from state $s _ { m }$ to $s _ { m } ^ { \prime }$ based on the action $a _ { m } ,$ i.e., deferring the parcel or adding it to the auction pool. 

• Reward Function $R _ { m } : S _ { m } \times A _ { m } \to \mathbb { R } ^ { + }$ . The reward for agent $\tau$ taking an action is defined as the local platform’s revenue from successfully completing $\tau _ { \cdot }$ , formulated as: 

$$
R _ {m} (s _ {m}, a _ {m}) = \left\{ \begin{array}{c l} p _ {\tau} - R c (\tau , c) & \text {i f} a _ {m} = 0 \text {a n d} \mathbb {I} (\tau) = 1 \\ p _ {\tau} - p _ {\tau} ^ {\prime} (\tau , c) & \text {i f} a _ {m} = 1 \text {a n d} \mathbb {I} (\tau) = 1 \\ 0 & \text {o t h e r w i s e} \end{array} \right.
$$

where $\mathbb { I } ( \cdot ) \in \{ 0 , 1 \}$ is a binary indicator that 1 denotes successful allocation and 0 indicates otherwise. It is important to note that if a parcel $\tau$ is not assigned, i.e., $\bar { \mathbb { I } } ( \bar { \tau } ) = 0 ,$ , it reappears as a new agent in the next batch to re-evaluate the cross-or-not decision. 

We leverage the Double Deep Q-learning Network (DDQN) to address the MDPs $M _ { b }$ and $M _ { m }$ . Since it effectively mitigates the overestimation bias inherent in standard Qlearning by utilizing a separate target network for action selection [28], [36]. Notably, in $M _ { m } ,$ the number of decision agents (i.e., parcels) varies dynamically across matching batches, making decentralized learning approaches, in which each agent maintains an independent neural network, infeasible due to the unpredictability of agent count and computational overhead. To tackle this challenge, we adopt a centralized Q-network framework [13], where all agents share a common Q-function that generalizes across varying parcel states and actions. 

Discussion. The two RL-based processes in RL-CAPA, i.e., batch size partitioning $( M _ { b } )$ and cross-or-not parcel assignment $( M _ { m } ) .$ , are closely coupled and mutually affect. The batch size determined by $M _ { b }$ directly affects $M _ { m }$ by shaping the number and urgency of parcels within each batch. Smaller batches enable more responsive decision-making, while larger batches enhance matching efficiency under low-load conditions. Conversely, the actions of $M _ { m } ,$ such as delaying to the next batch or entering the auction pool, influence future states observed by $M _ { b } ,$ guiding adaptive adjustments to batch duration. To exploit this bidirectional dependency and enable better coordination between global and local decision layers, we jointly train the DDQN models for $M _ { b }$ and $M _ { m }$ . During joint training, the shared environment is updated based on the combined outcomes of both 


TABLE 2 Parameter Settings


<table><tr><td>Parameters</td><td>Values</td></tr><tr><td># of couriers |C| (NYTaxi)</td><td>0.1K, 0.2K, 0.3K, 0.4K, 0.5K</td></tr><tr><td># of Parcels |Γ| (NYTaxi)</td><td>0.5K, 2k, 5K, 10K, 20K</td></tr><tr><td># of couriers |C| (Synthetic)</td><td>1K, 2K, 3K, 4K, 5k</td></tr><tr><td># of Parcels |Γ| (Synthetic)</td><td>5k, 20K, 50K, 100K, 200K</td></tr><tr><td>Capacity of courier w</td><td>25, 50, 75, 100, 125</td></tr><tr><td>Courier service radius rad (km)</td><td>0.5, 1, 1.5, 2, 2.5</td></tr><tr><td># of cooperating platforms P</td><td>2,4,8,12,16</td></tr></table>

decision processes, allowing each agent to account for the downstream impact of its actions and improve long-term revenue optimization under dynamic system conditions. 

# 4 EXPERIMENTAL EVALUATION

In this section, we evaluate the efficiency and effectiveness of the proposed methods on both real and synthetic datasets. 

# 4.1 Experimental Setup

Data and parameters. We conduct experiments using two datasets: the NYTaxi dataset1 and a synthetic dataset. The NYTaxi dataset contains one month of taxi trajectory data from New York City. The synthetic dataset is constructed from real-world logistics data across multiple cooperating platforms in Shanghai, simulating parcel pick-up and dropoff activities. We randomly sample parcels and extract pickup/drop-off points and time information from actual taxi trajectories. The arrival sequence of parcels is simulated based on their order of appearance. For the road network, we use OpenStreetMap data2: Shanghai’s network includes 216,225 edges and 14,853 nodes, while New York’s includes 8,635,965 edges and 157,628 nodes. Since parcel weights are not provided in either dataset, we randomly assign weights from a uniform distribution over (0, 10). Courier preference coefficients $\alpha _ { c _ { P } ^ { i } }$ and $\beta _ { c _ { P } ^ { i } }$ are also generated uniformly, following the method in [15]. In practical deployment, these coefficients can be presented as selectable options for couriers and platforms [21]. The deadlines for parcels, $t _ { \tau }$ and $t _ { \phi }$ , are set to range from 0.5 to 24 hours based on real-world scenarios [21], [22]. For the DQN implementation, we use the RMSprop optimizer [7] with a learning rate of 0.001 and a discount factor of 0.9. All parameter settings, including default and key values, are summarized in Table 2, with key parameters highlighted in bold. 

Compared methods. We compare our proposed algorithms CAPA (standard algorithm) and RL-CAPA (RL-based algorithm) with existing algorithms, including RamCOM [6], RMA [21], and Greedy [21]. 

Evaluation metrics and implements. The performance of the matching algorithms is evaluated using three key metrics: (i) Total Revenue (TR): The combined revenue from both local and cross-platform task completions; (ii) Completion Rate (CR): The ratio of tasks completed (locally and cooperatively) to the total number of local tasks; (iii) Batch Processing Time (BPT): The elapsed time from the 

1. https://www.nyc.gov 

2. https://www.openstreetmap.org 

beginning of each matching round to the completion of all task assignments within that round. All algorithms are implemented in Python and evaluated on a PC equipped with an Intel i7-9700K@3.6GHz CPU and 16GB RAM. 

# 4.2 Performance Evaluation

We examine the performance of our proposed matching methods in the NYTaxi and Synthetic datasets. 

Exp-1: Effect of parcel number |Γ|: As shown in Fig. 6(a)(b)(c), the TR of all algorithms increases with the number of tasks |Γ|, though the growth is sublinear in the NYTaxi data. Among the methods, RL-CAPA, CAPA, and RamCom exhibit superior TR, particularly when $| \Gamma |$ exceeds the number of internal couriers, as they effectively leverage external couriers to serve additional requests. Notably, RL-CAPA and CAPA outperform RamCom due to their deferred matching and threshold-based task selection strategies, which prioritize high-value tasks to maximize platform revenue. For $| \Gamma | < 5 \mathrm { k } ,$ CAPA achieves the highest TR and CR. As $| \Gamma |$ increases, the CRs of RL-CAPA, CAPA, and Ram-Com remain stable initially, as more requests are fulfilled by external couriers. However, when $| \Gamma | > 5 \mathrm { k } ,$ their CRs drop significantly due to capacity saturation of both internal and external couriers, limiting further task acceptance. In terms of BPT, all algorithms exhibit increased processing time per batch as $| \Gamma |$ grows. his is because the CAPA and MRA algorithms use multiple rounds of matching, and when the number of packages increases and the time division is larger, the processing time for each batch is longer than that of the RL-CAPA, RamCom, and Greedy algorithms. The Greedy algorithm uses a greedy algorithm, and its processing time is the shortest. The results on revenue and completion ratio are similar to those for the NYTaxi dataset. 

Exp-2: Effect of courier number $| C |$ : From Fig. 6(d)(e)(f) and Fig. 7 (d)(e)(f) , it can be observed that as $| \Gamma |$ increases, both BPT and TR rise for all algorithms, while CR declines. When the number of couriers $| C | ~ < ~ 4 0 0$ in the NYTaxi dataset, the TR, CR, and BPT for all algorithms increase with $| C |$ . This indicates that a larger courier pool enables more pick-up tasks to be completed, thereby enhancing both revenue and task fulfillment. More specifically, Fig. 6(g) shows that RL-CAPA and CAPA achieve the most significant revenue growth. Similarly, Fig. 6(h) demonstrates that the CR improves across all algorithms, with RL-CAPA and CAPA achieving relatively higher rates, likely due to their strategies of not rejecting tasks when external policy constraints are considered. Among all methods, CAPA consistently achieves the highest TR and CR. As shown in Fig. 6(i), the BPT slightly increases with $| C |$ but the impact remains modest, suggesting that all algorithms maintain efficient processing even as the system scales. However, once $\begin{array} { r } { | C | { \bf \bar { \theta } } > 4 0 0 , } \end{array}$ , the growth of TR, CR, and BPT tends to plateau. This suggests that the majority of pick-up tasks are already being served and that the marginal benefit of adding more couriers diminishes. Thus, after reaching a certain scale, increasing the number of couriers yields limited improvements in platform performance and efficiency. The trends in TR, CR and BPT on the synthetic dataset are consistent with those observed in the NYTaxi dataset. 

Exp-3: Effect of courier radius |rad.|: Fig.6(g)(h)(i) and Fig.7(g)(h)(i) reports the impact of varying the service radius 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/ddcf4218664e9aa67dcb9a62a247fd1262a41a7baec9bd5bcf9f3468894c3735.jpg)



(a) TR VS. |Γ|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/352105a32a06534327764c0ff6259e440dc3a079a1751ab8ffe2707c2266336d.jpg)



(b) CR VS. |Γ|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/5baa43424bebb4f0212412830e7bf3b6416b3ba7c13fceaae6dbe4ddfe78d6ad.jpg)



(c) BPT VS. |Γ|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/7cbbacc18b2c3bcfe917fb014a5370da975ff11dffe99a38f0ea4adcd15398ab.jpg)



(d) TR VS. |C|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/d25f73a6fb6c49d8bc706dc039a12206e8d04b35de3dc9f95076cc01b23f0735.jpg)



(e) CR VS. |C|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/fd074e271a5c7bcf6604f8cd7303abe99f42870db4f75e653b405f6ca6f1cfb9.jpg)



(f) BPT VS. |C|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/dc5dc8d5195974dac00b16639d4ae7b3602e04740b06a9d9fcbd3481cd6367fe.jpg)



(g) TR VS. rad.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/4e2f6f125d56d8ca4dac9c5c81b59e931145f9ba2fa0159ddd500ede99844846.jpg)



(h) CR VS. rad.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/78a8245848796785f6b2f591266f13db38182a49b0c33a56a70467d3ffdebe39.jpg)



(i) BPT VS. rad.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/67e3d01c6796b0836a3bea9430e4b74cea7787ac9eb76c7e8fc7caff8bfc6931.jpg)



(j) TR VS. |P |


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/2f6837faaa3eac862025d903720fca3a96acceb569b2ba8a24aa2c1f8331bfa8.jpg)



(k) CR VS. |P |


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/9f8b5f3479815de450b377665539bcb9eb84d03abbed0f35352526fc3e192f14.jpg)



(l) BPT VS. |P |



Fig. 6. Matching results by varying |Γ|, $| C |$ , rad and $| \mathcal { P } |$ on NYTaxi dataset.


|rad| (from 0.5 km to $2 . 5 \ \mathrm { k m } ,$ ) on algorithm performance across both the NYTaxi and Synthetic datasets. Overall, enlarging the service radius leads to increased TR across all algorithms, particularly benefiting RL-CAPA, which consistently outperforms CAPA and other baselines. This advantage is attributed to RL-CAPA’s superior ability to manage cooperative parcel assignments, as a larger service area enables couriers to access and fulfill more requests, thereby boosting platform revenue. In terms of completion ratio (CR), when $| r a d |$ is small (e.g., $\mathrm { : 1 . 5 ~ k m } $ , RL-CAPA and CAPA both show steady improvements due to the expanded coverage allowing more parcels to be served by both internal and external couriers. As the radius continues to increase, CR growth tends to stabilize since most parcels have already been matched and delivered. Notably, baseline methods such as MBA and Greedy continue to benefit from increasing $| r a d | ,$ , likely because the limited number of local couriers gains greater access to parcels over the enlarged area. Batch processing time (BPT) also increases moderately with larger $| r a d | ,$ especially for CAPA and MRA, due to the additional overhead in identifying suitable couriers from a broader area. Nevertheless, BPT stabilizes as courier capacity approaches saturation, indicating that the system maintains acceptable efficiency even under expanded operational scopes. Importantly, both datasets exhibit similar performance trends across all metrics, which validates the robustness of the proposed RL-CAPA algorithm under varying urban logistics scenarios. 

Exp-4: Effect of cooperating platform number $| \mathcal { P } |$ : Fig. 6 (j)(k)(l) and Fig. 7 (j)(k)(l) report the effect of cooperating platform number $| \mathcal { P } |$ for cross-based algorithms, i.e., RL-CAPA, CAPA, and RamCOM. Evidently, as the number of cooperating platforms increases, the task completion rate of the local platform significantly improves, eventually approaching $1 0 0 \%$ . This is because more cooperating platforms introduce a greater number of available workers, thereby continuously enhancing task fulfillment efficiency. Notably, despite the involvement of additional cooperating platforms, the BPT of all algorithms remains largely unchanged. This can be attributed to the fact that all cooperating platforms participate in independent sealed-bid auctions, where bidding is conducted without cross-platform interactions, 

making the number of platforms have minimal impact on BPT. Furthermore, when a large number of cooperating platforms are involved, the task completion rates of all algorithms approach $1 0 0 \%$ . However, under such conditions, CAPA achieves higher total platform revenue compared to RamCOM. This is due to its use of delayed matching and threshold-based task selection strategies, which prioritize high-value tasks to maximize platform profits. In contrast, RL-CAPA outperforms the heuristic-based CAPA in terms of platform revenue, as its reinforcement learning approach can handle more complex matching scenarios and optimize task allocation quality from a long-term perspective. 

Exp-5: Results under default settings: As reported in Fig. 8, under default experimental settings in the NYTaxi dataset, RL-CAPA consistently outperforms all baselines across key metrics. Specifically, in terms of CR, it achieves a relative improvement of $1 . 8 6 \%$ over CAPA and $1 2 . 3 3 \%$ , $2 6 . 1 5 \% ,$ and $3 6 . 6 7 \%$ over RamCom, MRA, and Greedy, respectively. In terms of TR, RL-CAPA improves upon CAPA by $1 . 8 2 \%$ , RamCom by $1 0 . 1 9 \% ,$ and MRA and Greedy by $3 8 . 4 1 \%$ and $5 3 . 3 4 \%$ , respectively. Despite its learning-based decision-making, RL-CAPA maintains a low batch processing time of 0.08s, which is $6 0 \%$ faster than CAPA and comparable to other baselines. These results demonstrate that RL-CAPA not only enhances assignment effectiveness and economic returns but also ensures high computational efficiency, making it well-suited for real-time cooperative logistics scenarios. Similar experimental results on the Synthetic dataset also support the superiority of the proposed methods RL-CAPA and CAPA in terms of efficiency and effectiveness. 

In summary, the two proposed algorithms, i.e., CAPA and RL-CAPA, suit different application scenarios. RL-CAPA is recommended for environments with high realtime requirements and large task volumes, while CAPA is better suited for scenarios with lower real-time demands and smaller task scales. Both algorithms effectively achieve resource allocation. 

# 5 LITERATURE REVIEW

In this section, we survey the related works of task assignment and auction mechanisms. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/b43c3f3054a985d3628ebc1749b7dc9808fa3b6a731b225162af8b71702a516f.jpg)



(a) TR VS. |Γ|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/d6b256080390c9139ab8640a3ddb1ed1fc6832456abf6bac5d9e477007aa6c6b.jpg)



(b) CR VS. |Γ|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/586abb6c42f8c9456a2defd8e42afc68e93c52cedd44b3c25698e3522d027a76.jpg)



(c) BPT VS. |Γ|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/7f19990330ec31da9c6e3ddd9e856e97e552da15f3d5e2666c5b810ba0d82c05.jpg)



(d) TR VS. |C|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/dd9ff52cd1187804934180291a6bb09b6466399206d1af4de7d2800dd01e06fe.jpg)



(e) CR VS. |C|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/671fba974bbcd19b66ac0c6e6f4d446afa30cfb1a613c60dfb294802f0acb82a.jpg)



(f) BPT VS. |C|


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/a43b7e41567e33a52be428d20e03e76e62d54e0b235612e1d3a45a641bc11014.jpg)



(g) TR VS. rad.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/31b88d587bbe578868692596d228422ab653ba0ab094a1aa4965455217590e69.jpg)



(h) CR VS. rad.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/3916f671b38c3d78930a0b7a3aaea4392ee6dee29ba5e77654b1a99ed3f5888f.jpg)



(i) BPT VS. rad.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/c2db1c00914791c4be4f7419a8955d2fdb5ddbb02e5a7e726f2acaa06edfc1ae.jpg)



(j) TR VS. |P |


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/032e0034c474b010b6e02c795f924da69b0e34aba712847079cf50b6a476214a.jpg)



(k) CR VS. |P |


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/c03b9bbca56dcaaaa629cccb763b3be337b0ee38c6415fa410f292cbe11fa57f.jpg)



(l) BPT VS. |P |



Fig. 7. Matching results by varying |Γ|, $| C |$ , rad and $| \mathcal { P } |$ on synthetic datasets.


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/dbfa33d9b7720a96d98a13a7838df524a5f5725800eacfcaea32fa1b4ceeeb6e.jpg)



(a) Default VS. TR


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/fb244d8b14b038f45a7c8209cbf21dc732179bf6118eb02c4439e0166a8f4c2a.jpg)



(b) Default VS. CR


![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/3fa7a3dd601e23ee8f3fa0f2e8d94d40e80f7aa3e5b5cc409d15ad8312143d3f.jpg)



(c) Default VS. BPT



Fig. 8. Matching results under default settings on NYTaxi and synthetic datasets.


# 5.1 Task Assignment

In SC, online task assignment refers to the process of finding suitable service providers for sequentially arriving tasks [20], [49], [50]. 

Recent years have witnessed significant advancements in SC research, particularly in the domain of task collaboration [6], [44], [17], [38]. Cheng et al. [6] introduced the concept of Cross-Online Matching (COM), enabling platforms to borrow idle crowd workers from one another to improve task distribution efficiency. While this approach promotes cooperation between platforms, it overlooks the potential complexities of worker behavior and platformspecific constraints, which can limit its scalability in realworld scenarios. Yang et al. [44] developed a Batch-based Collaborative Task Allocation (BCTA) method to reduce task distribution times across multiple platforms. Although this method improves task execution speed, it still faces challenges in handling dynamic task arrival patterns and optimizing long-term performance across platforms. Li et al. [17] proposed a Global Task Allocation (GTA) method that focuses on optimizing worker distribution at a platform level rather than on an individual basis, aiming to increase overall revenue. However, this platform-centric approach may disregard the nuances of individual task preferences and worker availability, potentially resulting in suboptimal matching efficiency. 

Furthermore, the role of reinforcement learning in SC has gained increasing attention in recent studies, particularly in resource allocation [32], [35], [51], [22] and decision-making [48], [10]. Shan et al. [32] proposed a deep reinforcement learning (DRL) framework for crowdsourcing task scheduling, focusing on long-term reward estimation. While this 

approach captures the future impact of task assignments, it fails to fully address the challenge of balancing shortterm operational constraints with long-term goals. Tong et al. [35] introduced a learning-to-dispatch (Ltd) system that integrates RL and combinatorial optimization for large-scale taxi dispatching. While the model effectively handles largescale dispatching, its focus on taxi orders limits its applicability to other types of dynamic, task-driven crowdsourcing scenarios. Li et al. [22] proposed a DRL-based method to dynamically adjust sliding window sizes, improving task matching. However, this approach still struggles with realtime responsiveness and does not fully capture the dynamic and complex nature of worker-task interactions in realworld environments. 

While these studies have made valuable contributions, they fail to adequately address the dynamic, real-time nature of task assignment with respect to multi-platform cooperation and long-term optimization. The limitations of existing approaches highlight the need for more adaptive and cooperation-aware mechanisms to address the CPUL problem. 

# 5.2 Auction Mechanism

Auction models have emerged as innovative mechanisms that efficiently motivate bidders to bid truthfully for items. These models have found widespread application in crowdsourcing (SC) to incentivize service providers’ participation in task assignment. 

As a fundamental motivating mechanism for resource allocation, auction models have garnered considerable attention in the SC field, with various research contributions addressing different aspects of auction models [21], [27], [43], [39], among others. For instance, Li et al. [21] proposed an Auction-Based Crowdsourcing FLML (ACF) problem, in which the platform allocates tasks based on courier preferences to maximize social welfare for both the platform and couriers. Hu et al. [27] introduced a mobile crowdsourcing incentive mechanism combining reverse and multi-attribute auctions, aiming to enhance participation. Yang et al. [43] designed a decision-making mechanism based on Stackelberg games, proving the existence of a unique equilibrium that maximizes utility. Wei et al. [39] presented a new honest 

double auction framework to ensure the authenticity of auctions in complex scenarios. 

However, these studies predominantly focus on singlelayer auction mechanisms and do not account for the twolayer auctions of the CPUL problem, where both cooperating platforms and their couriers participate in separate but interrelated bidding processes. As a result, existing auction models are insufficient to support the dual-layer bidding requirements inherent in cross-platform parcel allocation. 

# 6 CONCLUSION AND FUTURE WORK

In this paper, we propose the CAPA framework to address the CPUL problem. This framework effectively alleviates the issue of spatiotemporal imbalance between parcels and couriers. Specifically, we design a baseline algorithm, i.e., CAPA, to address the CPUL algorithm to maximize the local platform’s revenue while promoting efficient and fair resource allocation across platforms. Additionally, we introduce the RL-CAPA algorithm to further optimize global parcel assignment strategies. Extensive experimental results on NYTaxi and Synthetic datasets demonstrate the effectiveness and efficiency of our proposed algorithms. 

As for future work, we plan to extend this work in two directions: First, large language models (LLMs) can provide effective guidance for the intelligent decisions made by the customized model RL-CAPA. We thus plan to develop an efficient solution that integrates LLMs with a customized model to collaboratively address the CUPL problem, which further enhances the revenue of cooperating platforms. Second, accurate supply-demand forecasting is critical for RL-based decision models to optimize platform revenue through anticipatory decision-making. To this end, we leverage rich spatiotemporal data, such as trajectory density and historical order records, to predict future supply-demand distributions and strengthen the RL agent’s policy learning. 

# ACKNOWLEDGMENTS

This work is supported by the following grants: NSFC Grants 62372416, 62325602, 62402453, 62036010, and 61972362; HNSF Grant 242300421215. 

# REFERENCES



[1] Amazon. https://www.amazon.com. 





[2] Cainiao. https://www.caoniao.com. 





[3] JD Logistics. https://www.jdl.com/. 





[4] F. M. Bergmann, S. M. Wagner, and M. Winkenbach. Integrating first-mile pickup and last-mile delivery on shared vehicle routes for efficient urban e-commerce distribution. Transportation Research Part B: Methodological, 131:26–62, 2020. 





[5] A. Charisis, C. Iliopoulou, and K. Kepaptsoglou. Drt route design for the first/last mile problem: model and application to athens, greece. Public Transport, 10:499–527, 2018. 





[6] Y. Cheng, B. Li, X. Zhou, Y. Yuan, G. Wang, and L. Chen. Real-time cross online matching in spatial crowdsourcing. In 2020 IEEE 36th international conference on data engineering (ICDE), pages 1–12, 2020. 





[7] R. Elshamy, O. Abu-Elnasr, M. Elhoseny, and S. Elmougy. Improving the efficiency of rmsprop optimizer by utilizing nestrove in deep learning. Scientific Reports, 13(1):8814, 2023. 





[8] H. Fang and S. Morris. Multidimensional private value auctions. Journal of Economic Theory, 126(1):1–30, 2006. 





[9] X. Feng, F. Chu, C. Chu, and Y. Huang. Crowdsource-enabled integrated production and transportation scheduling for smart city logistics. International Journal of Production Research, 59(7):2157– 2176, 2021. 





[10] Z. Gu, T. Yin, and Z. Ding. Path tracking control of autonomous vehicles subject to deception attacks via a learning-based eventtriggered mechanism. IEEE Transactions on Neural Networks and Learning Systems, 32(12):5644–5653, 2021. 





[11] Y. Huang, X. Qiao, J. Tang, P. Ren, L. Liu, C. $\mathrm { P u } ,$ and J. Chen. An integrated cloud-edge-device adaptive deep learning service for cross-platform web. IEEE Transactions on Mobile Computing, 22(4):1950–1967, 2021. 





[12] G. Ke, H.-L. Du, and Y.-C. Chen. Cross-platform dynamic goods recommendation system based on reinforcement learning and social networks. Applied Soft Computing, 104:107213, 2021. 





[13] J. Ke, F. Xiao, H. Yang, and J. Ye. Learning to delay in ride-sourcing systems: A multi-agent deep reinforcement learning framework. IEEE Transactions on Knowledge and Data Engineering, 34(5):2280– 2292, 2022. 





[14] X. Kong, X. Liu, B. Jedari, M. Li, L. Wan, and F. Xia. Mobile crowdsourcing in smart cities: Technologies, applications, and future challenges. IEEE Internet of Things Journal, 6(5):8095–8113, 2019. 





[15] I. Krontiris and A. Albers. Monetary incentives in participatory sensing using multi-attributive auctions. International Journal of Parallel, Emergent and Distributed Systems, 27:317–336, 2012. 





[16] H. W. Kuhn. The hungarian method for the assignment problem. Naval research logistics quarterly, 2(1-2):83–97, 1955. 





[17] B. Li, Y. Cheng, Y. Yuan, C. Li, Q. Jin, and G. Wang. Competition and cooperation: Global task assignment in spatial crowdsourcing. IEEE Transactions on Knowledge and Data Engineering, 35(10):9998– 10010, 2023. 





[18] B. Li, Y. Cheng, Y. Yuan, Y. Yang, Q. Jin, and G. Wang. Acta: autonomy and coordination task assignment in spatial crowdsourcing platforms. Proceedings of the VLDB Endowment, 16(5):1073–1085, 2023. 





[19] Y. Li, H. Li, X. Huang, J. Xu, Y. Han, and M. Xu. Utility-aware dynamic ridesharing in spatial crowdsourcing. IEEE Transactions on Mobile Computing, 23(2):1066–1079, 2024. 





[20] Y. Li, H. Li, B. Mei, X. Huang, J. Xu, and M. Xu. Fairnessguaranteed task assignment for crowdsourced mobility services. IEEE Transactions on Mobile Computing, 23(5):5385–5400, 2023. 





[21] Y. Li, Y. Li, Y. Peng, X. Fu, J. Xu, and M. Xu. Auction-based crowdsourced first and last mile logistics. IEEE Transactions on Mobile Computing, 23(1):180–193, 2022. 





[22] Y. Li, Q. Wu, X. Huang, J. Xu, W. Gao, and M. Xu. Efficient adaptive matching for real-time city express delivery. IEEE Transactions on Knowledge and Data Engineering, 35(6):5767–5779, 2023. 





[23] Y. Li, Q. Wu, X. Huang, J. Xu, W. Gao, and M. Xu. Efficient adaptive matching for real-time city express delivery. IEEE Transactions on Knowledge and Data Engineering, 35(6):5767–5779, 2023. 





[24] Z. Liu, G. Xiao, X. Zhou, Y. Qin, Y. Gao, and K. Li. Cross online assignment of hybrid task in spatial crowdsourcing. In 2024 IEEE 40th International Conference on Data Engineering (ICDE), pages 317– 329, 2024. 





[25] E. Macioszek. First and last mile delivery–problems and issues. In Advanced Solutions of Transport Systems for Growing Mobility: 14th Scientific and Technical Conference” Transport Systems. Theory & Practice 2017” Selected Papers, pages 147–154, 2018. 





[26] A. C. Mckinnon. A communal approach to reducing urban traffic levels. K ¨uhne Logistics University: Hamburg, Germany, 2016. 





[27] A. Mehta et al. Online matching and ad allocation. Foundations and Trends® in Theoretical Computer Science, 8(4):265–368, 2013. 





[28] V. Mnih, K. Kavukcuoglu, D. Silver, A. A. Rusu, J. Veness, M. G. Bellemare, A. Graves, M. Riedmiller, A. K. Fidjeland, G. Ostrovski, et al. Human-level control through deep reinforcement learning. nature, 518(7540):529–533, 2015. 





[29] J. Pinkse and G. Tan. The affiliation effect in first-price auctions. Econometrica, 73(1):263–277, 2005. 





[30] E. Pourrahmani and M. Jaller. Crowdshipping in last mile deliveries: Operational challenges and research opportunities. Socio-Economic Planning Sciences, 78:101063, 2021. 





[31] T. Ren, X. Zhou, and et al. Efficient cross dynamic task assignment in spatial crowdsourcing. In 2023 IEEE 39th International Conference on Data Engineering (ICDE), pages 1420–1432, 2023. 





[32] C. Shan, N. Mamoulis, R. Cheng, G. Li, X. Li, and Y. Qian. An endto-end deep rl framework for task arrangement in crowdsourcing platforms. In 2020 IEEE 36th International Conference on Data Engineering (ICDE), pages 49–60, 2020. 





[33] O. Stopka, K. Jerˇabek, and M. Stopkov ´ a. Using the operations ´ research methods to address distribution tasks at a city logistics scale. Transportation Research Procedia, 44:348–355, 2020. 





[34] A. Suzdaltsev. Distributionally robust pricing in independent private value auctions. Journal of Economic Theory, 206:105555, 2022. 





[35] Y. Tong, D. Shi, Y. Xu, W. Lv, Z. Qin, and X. Tang. Combinatorial optimization meets reinforcement learning: Effective taxi order dispatching at large-scale. IEEE Transactions on Knowledge and Data Engineering, 35(10):9812–9823, 2021. 





[36] H. Van Hasselt, A. Guez, and D. Silver. Deep reinforcement learning with double q-learning. In Proceedings of the AAAI conference on artificial intelligence, volume 30, 2016. 





[37] Y. Wang, Y. Tong, and et al. Adaptive dynamic bipartite graph matching: A reinforcement learning approach. In 2019 IEEE 35th international conference on data engineering (ICDE), pages 1478–1489, 2019. 





[38] Y. Wang, Y. Tong, Z. Zhou, Z. Ren, Y. Xu, G. Wu, and W. Lv. Fedltd: Towards cross-platform ride hailing via federated learning to dispatch. In Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining, pages 4079–4089, 2022. 





[39] Y. Wei, Y. Zhu, H. Zhu, Q. Zhang, and G. Xue. Truthful online double auctions for dynamic mobile crowdsourcing. In 2015 IEEE Conference on Computer Communications (INFOCOM), pages 2074– 2082, 2015. 





[40] S. Wu, Y. Wang, and X. Tong. Multi-objective task assignment for maximizing social welfare in spatio-temporal crowdsourcing. China Communications, 18(11):11–25, 2021. 





[41] K. Xia, L. Lin, S. Wang, H. Wang, D. Zhang, and T. He. A predictthen-optimize couriers allocation framework for emergency lastmile logistics. In Proceedings of the 29th ACM SIGKDD Conference on Knowledge Discovery and Data Mining, pages 5237–5248, 2023. 





[42] K. Xia, L. Lin, S. Wang, H. Wang, D. Zhang, and T. He. A predictthen-optimize couriers allocation framework for emergency lastmile logistics. In Proceedings of the 29th ACM SIGKDD Conference on Knowledge Discovery and Data Mining, pages 5237–5248, 2023. 





[43] D. Yang, G. Xue, X. Fang, and J. Tang. Crowdsourcing to smartphones: Incentive mechanism design for mobile phone sensing. In Proceedings of the 18th annual international conference on Mobile computing and networking, pages 173–184, 2012. 





[44] Y. Yang, Y. Cheng, Y. Yang, Y. Yuan, and G. Wang. Batchbased cooperative task assignment in spatial crowdsourcing. In 2023 IEEE 39th International Conference on Data Engineering (ICDE), pages 1180–1192, 2023. 





[45] J. Yao, L. Yang, and et al. Online dependent task assignment in preference aware spatial crowdsourcing. IEEE Transactions on Services Computing, 16(4):2827–2840, 2023. 





[46] Y. Zeng, Y. Tong, and L. Chen. Last-mile delivery made practical: An efficient route planning framework with theoretical guarantees. Proceedings of the VLDB Endowment, 13(3):320–333, 2019. 





[47] X. Zhan, W. Szeto, C. Shui, and X. M. Chen. A modified artificial bee colony algorithm for the dynamic ride-hailing sharing problem. Transportation Research Part E: Logistics and Transportation Review, 150:102124, 2021. 





[48] J. Zhang, Y. Liu, K. Zhou, G. Li, Z. Xiao, B. Cheng, J. Xing, Y. Wang, T. Cheng, L. Liu, et al. An end-to-end automatic cloud database tuning system using deep reinforcement learning. In Proceedings of the 2019 international conference on management of data, pages 415– 432, 2019. 





[49] S. Zhang, L. Qin, Y. Zheng, and H. Cheng. Effective and efficient: Large-scale dynamic city express. pages 1–4, 2015. 





[50] Y. Zhao, K. Zheng, Z. Wang, L. Deng, B. Yang, T. B. Pedersen, C. S. Jensen, and X. Zhou. Coalition-based task assignment with priority-aware fairness in spatial crowdsourcing. The VLDB Journal, 33(1):163–184, 2024. 





[51] M. Zhou, J. Jin, W. Zhang, Z. Qin, Y. Jiao, C. Wang, G. Wu, Y. Yu, and J. Ye. Multi-agent reinforcement learning for orderdispatching via order-vehicle distribution matching. In Proceedings of the 28th ACM International Conference on Information and Knowledge Management, pages 2645–2653, 2019. 



![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/08c6fd70c093a6576c473e601374b88431fd03f09cc81213d3c92315eeca22b5.jpg)


Jiawen Zhang received the BEng degree in computer science and technology from Henan University of Technology, China, in 2022. She is currently working toward the MEng degree at the School of Computer and Artificial Intelligence, Zhengzhou University. Her research interests mainly focus on location-based services, multi-agent computing, and spatio-temporal data management. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/71498331ede79e35e9d9f8903b4c0c33a05a8535c9fdda6fb54a63e7b839a194.jpg)


Shuo He received the PhD degree in Information and Communication Engineering from Beijing University of Posts and Telecommunications (BUPT), China, in 2020. She is currently a lecturer in the School of Computer and Artificial Intelligence, Zhengzhou University, China. Her research interests include optimization, learning, as well as their applications to resource management and crowd computing. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/17ba95528556de8e29e3ef0d180e2b59a9a71b34f8834f936512859621d1707d.jpg)


Xuhui Song received the BEng degree in Software Engineering from Zhengzhou University, in 2024. He is currently working toward the MEng degree in the School of Computer and Artificial Intelligence, Zhengzhou University, China. His research interests include multi-agent computing, deep learning, and spatiotemporal data processing. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/1d6766270ddff1269e89a6dbfe47dd1853e307e85deb4a39abc02c959dd9d983.jpg)


Yafei Li received the PhD degree in computer science from Hong Kong Baptist University, in 2015. He is currently a professor in the School of Information Engineering of Zhengzhou University. His research interests span mobile and spatial data management, location-based services, and urban computing. He has authored more than 20 journal and conference papers in these areas, including IEEE TKDE, IEEE TSC, ACM TWEB, ACM TIST, PVLDB, IEEE ICDE, WWW, etc. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/07b7fef703da9fa10f8750e99a21251524a7426fd7091fa6c1b278142ce94ab7.jpg)


Jianliang Xu received the BEng degree in computer science and engineering from Zhejiang University, Hangzhou, China, and the PhD degree in computer science from the Hong Kong University of Science and Technology. He is a professor in the Department of Computer Science, Hong Kong Baptist University. He held visiting positions with Pennsylvania State University and Fudan University. His research interests include big data management, mobile computing, and data security and privacy. He has published 

more than 200 technical papers in these areas. He has served as a program co-chair/vice chair for a number of major international conferences including IEEE ICDCS 2012, IEEE CPSNA 2015, and APWeb-WAIM 2018. He is an associate editor of the IEEE Transactions on Knowledge and Data Engineering and the Proceedings of the VLDB Endowment 2018. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/429f42af95b2ee07712072cb1cd68be0db15f619eb04af2080a58da833b8f1e5.jpg)


Guanglei Zhu received the BEng degree and MEng degree in computer science and technology from Zhengzhou University, in 2018 and 2021. He is currently working toward the PhD degree in the School of Computer and Artificial Intelligence, Zhengzhou University, China. His research interests include multi-agent computing, deep learning, spatiotemporal data processing, and spatial intelligence. 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-03-31/01849a1e-1717-445a-9278-47d5a4b5d4d0/ee0d83f188f766fcf7ea47ccd87791f19d9997392d37832456a4748fe3684173.jpg)


Mingliang Xu received the PhD degree from the State Key Lab of CAD&CG, Zhejiang University, China. He is a professor in the School of Computer and Artificial Intelligence of Zhengzhou University, China. His current research interests include computer graphics, multimedia, and artificial intelligence. He has authored more than 60 journal and conference papers in these areas, including ACM TOG, IEEE TPAMI/TIP/TCSVT, ACM SIGGRAPH (Asia)/MM, ICCV, etc. 