(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x3118 (bvor (bvshl i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x1572 (bvor (bvlshr i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x6731 (ite (and (distinct ?x1572 ?x3118) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x6731 (_ bv1 1)))))))
(assert
 (let (($x794 (= i_4 (_ bv7 3))))
(not $x794)))
(check-sat)
