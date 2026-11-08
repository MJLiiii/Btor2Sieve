(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x1148 (bvor (bvshl i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x3512 (bvor (bvlshr i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x118 (ite (and (distinct ?x3512 ?x1148) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x118 (_ bv1 1)))))))
(assert
 (let ((?x3512 (bvor (bvlshr i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
(let (($x474 (and (distinct ?x3512 (_ bv3 3)) true)))
(not $x474))))
(check-sat)
