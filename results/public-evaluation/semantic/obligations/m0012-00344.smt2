(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x50 (bvor (bvlshr i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
 (let ((?x311 (ite (and (distinct ?x50 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x311 (_ bv1 1))))))
(assert
 (let ((?x50 (bvor (bvlshr i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
(let (($x1873 (and (distinct ?x50 (_ bv2 3)) true)))
(not $x1873))))
(check-sat)
