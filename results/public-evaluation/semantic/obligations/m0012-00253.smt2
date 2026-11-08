(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x1722 (bvor (bvshl i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x1026 (bvor (bvlshr i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x728 (ite (and (distinct ?x1026 ?x1722) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x728 (_ bv1 1)))))))
(assert
 (let (($x751 (= i_4 (_ bv1 3))))
(not $x751)))
(check-sat)
