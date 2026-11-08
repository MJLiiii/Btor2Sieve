(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x3465 (bvule i_4 (_ bv1 32))))
(not $x3465)))
(check-sat)
