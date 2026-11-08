(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 2))
(declare-fun s_6 () (_ BitVec 2))
(assert
 (let ((?x140 (ite (= (_ bv3 2) s_7) (_ bv1 1) (_ bv0 1))))
 (let ((?x76 (ite (= (_ bv3 2) s_6) (_ bv1 1) (_ bv0 1))))
 (let ((?x71 (bvand ?x76 ?x140)))
 (not (= ?x71 (_ bv1 1)))))))
(assert
 (let (($x2394 (and (distinct s_7 (_ bv0 2)) true)))
(not $x2394)))
(check-sat)
