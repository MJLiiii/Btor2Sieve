(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x1988 (bvor (bvshl i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
 (let ((?x380 (ite (and (distinct ?x1988 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x380 (_ bv1 1))))))
(assert
 (let ((?x1988 (bvor (bvshl i_4 (bvurem (_ bv3 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv3 3) (_ bv3 3)))))))
(let (($x25 (bvuge ?x1988 (_ bv2 3))))
(not $x25))))
(check-sat)
